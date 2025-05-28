from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils.log import logging

from jao_backend.embeddings.service import EmbeddingService
from jao_backend.vacancies.models import Vacancy

from litellm.exceptions import (
    APIConnectionError,
    Timeout,
    ServiceUnavailableError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout
)

@shared_task(autoretry_for=RETRYABLE_EXCEPTIONS, retry_backoff=True)
def generate_embeddings_task(vacancy_id: int):
    """
    Celery task for async embedding generation

    Args:
    - vacancy_id: ID of Vacancy to process

    Raises:
    - ObjectDoesNotExist: If vacancy not found
    - Exception: Retries on transient failures

    """
    try:
        vacancy = Vacancy.objects.get(pk=vacancy_id)
        EmbeddingService().create_for_vacancy(vacancy)
    except ObjectDoesNotExist as e:
        logger.error(f"Vacancy {vacancy_id} not found")
        raise
    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retrying embedding generation for {vacancy_id}: {str(e)}")
        raise
