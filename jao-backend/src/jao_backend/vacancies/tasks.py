from celery.canvas import chain
from celery_singleton import Singleton
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from litellm.exceptions import APIConnectionError
from litellm.exceptions import RateLimitError
from litellm.exceptions import ServiceUnavailableError
from litellm.exceptions import Timeout
from jao_backend.embeddings.service import EmbeddingService
from jao_backend.vacancies.models import Vacancy


from jao_backend.common.celery import app as celery
from jao_backend.ingest.ingester.oleeo_ingest import OleeoIngest


logger = get_task_logger(__name__)

RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)


@celery.task(base=Singleton, autoretry_for=RETRYABLE_EXCEPTIONS, retry_backoff=True)
def embed_vacancies(limit=settings.JAO_BACKEND_VACANCY_EMBED_LIMIT):
    """
    Run embedding, on vacancies (limited by the setting `JAO_BACKEND_VACANCY_EMBED_LIMIT`).

    This is a singleton task as embedding typically.

    :return: Number of vacancies embedded.
    """
    vacancies = Vacancy.objects.filter(is_deleted=False).requires_embedding(limit=limit)

    logger.info(
        "Embed vacancies.  JAO_BACKEND_EMBEDDING_GENERATION_LIMIT=%s, vacancies to embed: %s",
        settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
        len(vacancies),
    )
    try:
        for vacancy in vacancies:
            EmbeddingService().create_for_vacancy(vacancy)
    except Exception as e:
        raise e
    finally:
        logger.info("Embedded %s vacancies", len(vacancies))

    return len(vacancies)


@celery.task(base=Singleton, lock_expires=60 * 60)
def ingest_vacancies(max_batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE):
    """
    Ingest data from OLEEO / R2D2.

    Once the vacancy data is ingested, further work is required, e.g. embedding,
    see `jao_backend.common.tasks` for orchestration tasks.
    """

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting Oleeo ingest with max_batch_size={max_batch_size}")
    ingester = OleeoIngest(max_batch_size=max_batch_size)
    ingester.do_ingest()


@celery.task()
def reset_ingest_lock():
    """
    In certain states the ingest lock may not be released properly.
    """
    pass


update_vacancies = chain(ingest_vacancies.s(), embed_vacancies.s())
"""
Ingest vacancies, and then start embedding.
"""
