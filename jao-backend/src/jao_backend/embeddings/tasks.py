import logging

from celery import shared_task
from celery_singleton import Singleton
from celery.utils.log import get_task_logger
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from litellm.exceptions import APIConnectionError
from litellm.exceptions import RateLimitError
from litellm.exceptions import ServiceUnavailableError
from litellm.exceptions import Timeout

from jao_backend.common.celery import app as celery
from jao_backend.embeddings.service import EmbeddingService
from jao_backend.vacancies.models import Vacancy

logger = get_task_logger(__name__)

RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)


@celery.task(base=Singleton, autoretry_for=RETRYABLE_EXCEPTIONS, retry_backoff=True)
def embed_vacancies():
    """
    Run embedding, on vacancies (limited by the setting `JAO_BACKEND_VACANCY_EMBED_LIMIT`).

    This is a singleton task as embedding typically
    """
    vacancies = Vacancy.objects.filter(is_deleted=False).requires_embedding()

    logger.info(
        "Embed vacancies.  JAO_BACKEND_EMBEDDING_GENERATION_LIMIT=%s, vacancies to embed: %s",
        settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
        len(vacancies),
    )
    for vacancy in vacancies:
        EmbeddingService().create_for_vacancy(vacancy)
