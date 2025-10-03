import json
import logging
import asyncio
from django.core.cache import cache
from channels.generic.websocket import AsyncWebsocketConsumer
from jao_web.common.text_processing.clean_oleeo import parse_oleeo_bbcode
from jao_web.job_advert_optimiser.services.client import get_async_client
from jao_web.job_advert_optimiser.services.services import (
    get_similar_adverts,
)

logger = logging.getLogger(__name__)


class JobAdvertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket connected")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: {close_code}")

    async def send_json(self, data):
        """Helper to send JSON data"""
        try:
            await self.send(json.dumps(data))
        except Exception as e:
            logger.exception("Error sending message")

    def store_in_session(self, session_key, data):
        """Store data in cache using session key"""
        cache_key = f"job_advert_{session_key}"
        cache.set(cache_key, data, timeout=3600)  # 1 hour timeout

    def get_from_session(self, session_key):
        """Retrieve data from cache using session key"""
        cache_key = f"job_advert_{session_key}"
        return cache.get(cache_key, {})

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            # default to original behavior
            message_type = data.get('type', 'process_description')
            match message_type:
                case 'get_advice':
                    await self.handle_get_advice(data)

                case 'get_draft':
                    await self.handle_get_draft(data)

                case 'process_description':
                    await self.handle_process_description(data)

                case _:
                    # Handle legacy behavior where 'job_description' in data
                    if 'job_description' in data:
                        await self.handle_process_description(data)
                    else:
                        await self.send_json({
                            'type': 'error',
                            'message': 'Unknown message type'
                        })
        except json.JSONDecodeError:
            logger.exception("Invalid JSON received")
            await self.send_json({
                'type': 'error',
                'message': 'Invalid request format'
            })
        except Exception as e:
            logger.exception("WebSocket error")
            await self.send_json({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            })

    async def handle_process_description(self, data):
        """Handle processing job description - get similar vacancies only"""
        job_description = data.get('job_description')
        session_key = data.get('session_key')

        if not job_description:
            await self.send_json({
                'type': 'error',
                'message': 'Job description is required'
            })
            return

        logger.info(f"Processing job description for similar vacancies: {
                    job_description[:100]}...")

        async with get_async_client(session_key) as client:
            await self._get_similar_adverts(client, job_description, session_key)

        await self.send_json({'type': 'complete'})

    async def handle_get_advice(self, data):
        """Handle getting advice only"""
        advice_category = data.get('advice_category')
        advice_type = data.get('advice_type')
        session_key = data.get('session_key')
        job_description = self.get_from_session(session_key)["job_description"]

        if not job_description:
            await self.send_json({
                'type': 'error',
                'message': 'Job description is required'
            })
            return

        async with get_async_client(session_key) as client:
            await self._get_advice(client, job_description, session_key, advice_type)

        await self.send_json({'type': 'advice_complete'})

    async def handle_get_draft(self, data):
        """Handle job description drafting"""
        session_key = data.get('session_key')
        job_description = self.get_from_session(session_key)["job_description"]

        if not job_description:
            await self.send_json({
                'type': 'error',
                'message': 'Job description is required'
            })
            return

        async with get_async_client(session_key) as client:
            await self._get_draft(client, job_description, session_key)

        await self.send_json({'type': 'draft_complete'})

    async def _get_advice(self, client, job_description, session_key, advice_type='general'):
        """Get advice from backend"""
        await self.send_json({
            'type': 'status',
            'message': 'Generating personalized advice...'
        })
        session_data = self.get_from_session(session_key)
        similar_vacancies = session_data['similar_vacancies']

        try:
            async with client.stream(
                "POST",
                "advice",
                json={
                    "description": job_description,
                    "advice_type": advice_type,
                    "similar_vacancies": similar_vacancies
                },
                timeout=300
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break

                        chunk_data = json.loads(data)
                        content = chunk_data.get('content', '')

                        await self.send_json({
                            'type': 'advice_chunk',
                            'data': content
                        })

            await self.send_json({'type': 'advice_complete'})

        except asyncio.TimeoutError:
            logger.error("Advice request timed out")
            await self.send_json({
                'type': 'error',
                'service': 'advice',
                'message': 'Request timed out after 5 minutes'
            })
        except Exception as e:
            logger.exception("Error getting advice")
            await self.send_json({
                'type': 'error',
                'service': 'advice',
                'message': str(e)
            })

    async def _get_draft(self, client, job_description, session_key):
        """Get drafted job description from backend"""
        await self.send_json({
            'type': 'status',
            'message': 'Draft job advert...'
        })
        session_data = self.get_from_session(session_key)
        similar_vacancies = session_data['similar_vacancies']
        try:
            async with client.stream(
                "POST",
                "draft",
                json={
                    "description": job_description,
                    "similar_vacancies": similar_vacancies
                },
                timeout=300
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break

                        chunk_data = json.loads(data)
                        content = chunk_data.get('content', '')

                        await self.send_json({
                            'type': 'draft_chunk',
                            'data': content
                        })

            await self.send_json({'type': 'draft_complete'})

        except asyncio.TimeoutError:
            logger.error("Similar adverts request timed out")
            await self.send_json({
                'type': 'error',
                'service': 'similar_vacancies',
                'message': 'Request timed out after 2 minutes'
            })
        except Exception as e:
            logger.exception("Error getting similar vacancies")
            await self.send_json({
                'type': 'error',
                'service': 'similar_vacancies',
                'message': str(e)
            })

    async def _get_similar_adverts(self, client, job_description, session_key):
        """Get similar adverts from backend"""
        await self.send_json({
            'type': 'status',
            'message': 'Finding similar job adverts...'
        })

        try:
            async with asyncio.timeout(120):
                similar_response = await get_similar_adverts(client, job_description)

            vacancies_data = [
                {
                    'vacancy_id': v.vacancy_id,
                    'job_title': v.job_title,
                    'full_job_desc': parse_oleeo_bbcode(v.full_job_desc)
                }
                for v in getattr(similar_response, 'similar_vacancies', [])
            ]

            self.store_in_session(session_key, {
                'job_description': job_description,
                'similar_vacancies': vacancies_data
            })

            await self.send_json({
                'type': 'similar_vacancies',
                'data': vacancies_data
            })

        except asyncio.TimeoutError:
            logger.error("Similar adverts request timed out")
            await self.send_json({
                'type': 'error',
                'service': 'similar_vacancies',
                'message': 'Request timed out after 2 minutes'
            })
        except Exception as e:
            logger.exception("Error getting similar vacancies")
            await self.send_json({
                'type': 'error',
                'service': 'similar_vacancies',
                'message': str(e)
            })
