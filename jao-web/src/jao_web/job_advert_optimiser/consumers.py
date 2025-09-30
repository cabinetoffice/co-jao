import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from jao_web.common.text_processing.clean_oleeo import parse_oleeo_bbcode
from jao_web.job_advert_optimiser.services.client import get_async_client
from jao_web.job_advert_optimiser.services.services import (
    get_advice,
    get_similar_adverts
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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            job_description = data.get('job_description')
            session_key = data.get('session_key')

            if not job_description:
                await self.send_json({
                    'type': 'error',
                    'message': 'Job description is required'
                })
                return

            logger.info(f"Processing job description: {
                        job_description[:100]}...")

            async with get_async_client(session_key) as client:
                advice_task = asyncio.create_task(
                    self._get_advice(client, job_description)
                )
                vacancies_task = asyncio.create_task(
                    self._get_similar_adverts(client, job_description)
                )

                await asyncio.gather(advice_task, vacancies_task)

            await self.send_json({'type': 'complete'})

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

    async def _get_advice(self, client, job_description):
        """Get advice from backend"""
        await self.send_json({
            'type': 'status',
            'message': 'Generating personalized advice...'
        })

        try:
            async with client.stream(
                "POST",
                "advice",
                json={"description": job_description},
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
                'message': 'Request timed out after 2 minutes'
            })
        except Exception as e:
            logger.exception("Error getting advice")
            await self.send_json({
                'type': 'error',
                'service': 'advice',
                'message': str(e)
            })

    async def _get_similar_adverts(self, client, job_description):
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
