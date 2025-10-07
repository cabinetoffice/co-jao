import json
import logging
import asyncio
from django.core.cache import cache
from channels.generic.websocket import AsyncWebsocketConsumer

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
            message_type = data.get('type', 'process_description')

            match message_type:
                case 'get_advice':
                    await self.handle_get_advice(data)
                case 'get_draft':
                    await self.handle_get_draft(data)
                case 'process_description':
                    await self.handle_process_description(data)
                case _:
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
        await self._get_similar_adverts(job_description, session_key)
        await self.send_json({'type': 'complete'})

    async def handle_get_advice(self, data):
        """Handle getting advice only"""
        advice_type = data.get('advice_type')
        session_key = data.get('session_key')
        job_description = self.get_from_session(
            session_key).get("job_description")

        if not job_description:
            await self.send_json({
                'type': 'error',
                'message': 'Job description is required'
            })
            return

        await self._get_advice(job_description, session_key, advice_type)

    async def handle_get_draft(self, data):
        """Handle job description drafting"""
        session_key = data.get('session_key')
        job_description = self.get_from_session(
            session_key).get("job_description")

        if not job_description:
            await self.send_json({
                'type': 'error',
                'message': 'Job description is required'
            })
            return

        await self._get_draft(job_description, session_key)

    async def _get_advice(self, job_description, session_key, advice_type='general'):
        """Get advice directly from LLM service"""
        await self.send_json({
            'type': 'status',
            'message': 'Generating personalized advice...'
        })

        session_data = self.get_from_session(session_key)
        similar_vacancies = session_data.get('similar_vacancies', [])

        formatted_vacancies = [
            f"Job Title: {v['job_title']}\nDescription: {v['full_job_desc']}"
            for v in similar_vacancies
        ]
        from jao_backend.llm.llm_service import LLMService
        llm_service = LLMService()

        try:
            for chunk in llm_service.get_advice(job_description, formatted_vacancies, advice_type):
                await self.send_json({
                    'type': 'advice_chunk',
                    'data': chunk
                })

            await self.send_json({'type': 'advice_complete'})

        except Exception as e:
            logger.exception("Error getting advice")
            await self.send_json({
                'type': 'error',
                'service': 'advice',
                'message': str(e)
            })

    async def _get_draft(self, job_description, session_key):
        """Get drafted job description from LLM service"""
        await self.send_json({
            'type': 'status',
            'message': 'Drafting job advert...'
        })

        session_data = self.get_from_session(session_key)
        similar_vacancies = session_data.get('similar_vacancies', [])

        formatted_vacancies = [
            f"Job Title: {v['job_title']}\nDescription: {v['full_job_desc']}"
            for v in similar_vacancies
        ]
        from jao_backend.llm.llm_service import LLMService
        llm_service = LLMService()
        try:
            for chunk in llm_service.generate_draft(job_description, formatted_vacancies):
                await self.send_json({
                    'type': 'draft_chunk',
                    'data': chunk
                })

            await self.send_json({'type': 'draft_complete'})

        except Exception as e:
            logger.exception("Error getting draft")
            await self.send_json({
                'type': 'error',
                'service': 'draft',
                'message': str(e)
            })

    async def _get_similar_adverts(self, job_description, session_key):
        """Get similar adverts directly from database"""
        await self.send_json({
            'type': 'status',
            'message': 'Finding similar job adverts...'
        })

        from jao_backend.common.text_processing.clean_oleeo import parse_oleeo_bbcode
        from jao_backend.vacancies.vacancy_service import get_similar_vacancies_cached
        try:
            similar_vacancies = await asyncio.to_thread(
                get_similar_vacancies_cached,
                job_description,
                top_n=10
            )

            vacancies_data = [
                {
                    'vacancy_id': v.pk,
                    'job_title': v.title,
                    'full_job_desc': parse_oleeo_bbcode(v.description)
                }
                for v in similar_vacancies
            ]

            self.store_in_session(session_key, {
                'job_description': job_description,
                'similar_vacancies': vacancies_data
            })

            await self.send_json({
                'type': 'similar_vacancies',
                'data': vacancies_data
            })

        except Exception as e:
            logger.exception("Error getting similar vacancies")
            await self.send_json({
                'type': 'error',
                'service': 'similar_vacancies',
                'message': str(e)
            })
