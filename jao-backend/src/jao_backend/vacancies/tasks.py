"""
The Celery tasks here wrap the functions that do the actual work.
"""

from celery.canvas import chain
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from litellm.exceptions import APIConnectionError
from litellm.exceptions import RateLimitError
from litellm.exceptions import ServiceUnavailableError
from litellm.exceptions import Timeout

from jao_backend.common.celery.active_singleton import ActiveSingleton
from jao_backend.common.db.connections import DatabaseConnectionLostError, on_db_disconnect_raise
from jao_backend.vacancies.embed import embed_vacancy
from jao_backend.vacancies.models import Vacancy


from jao_backend.common.celery import app as celery
from jao_backend.ingest.ingester.ingest_vacancies import OleeoVacanciesIngest
from jao_backend.ingest.ingester.ingest_aggregated_applicants import (
    OleeoApplicantStatisticsAggregator,
)

logger = get_task_logger(__name__)


RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    DatabaseConnectionLostError,
)

TASK_KWARGS = {
    "base": ActiveSingleton,
    "autoretry_for": RETRYABLE_EXCEPTIONS,
    "retry_backoff": True,
}

@celery.task(**TASK_KWARGS)
@on_db_disconnect_raise(using="oleeo")
def embed_vacancies(limit=settings.JAO_BACKEND_VACANCY_EMBED_LIMIT):
    """
    Run embedding, on vacancies (limited by the setting `JAO_BACKEND_VACANCY_EMBED_LIMIT`).

    This is a singleton task as embedding typically.

    :return: Number of vacancies embedded.
    """
    # Grab the vacancies that are not fully embedded yet, in reverse order so the newest are embedded first.
    vacancies = (
        Vacancy.objects.filter(is_deleted=False)
        .order_by("-id")
        .requires_embedding(limit=limit)
    )

    total_embedded = 0
    logger.info(
        "Embed vacancies.  JAO_BACKEND_EMBEDDING_GENERATION_LIMIT=%s, vacancies to embed: %s",
        settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
        len(vacancies),
    )
    try:
        for vacancy in vacancies:
            # Guard against concurrency by refetching the vacancy from the database.
            if not vacancy.get_requires_embedding():
                # If another task is running concurrently then the vacancy may have already been embedded.
                # This is an edge case, but worth avoiding.
                # The embedding takes longer than hitting the database with a query.
                logger.info("Vacancy %s already embedded, skipping.", vacancy.id)
                continue

            embed_vacancy(vacancy)
            total_embedded += 1
    except Exception as e:
        raise e
    finally:
        logger.info("Embedded %s/%s vacancies", total_embedded, len(vacancies))

    return len(vacancies)


@celery.task(**TASK_KWARGS)
@on_db_disconnect_raise(using="oleeo")
def ingest_vacancies(batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE):
    """
    Ingest data from OLEEO / R2D2.

    Once the vacancy data is ingested, further work is required, e.g. embedding,
    see `jao_backend.common.tasks` for orchestration tasks.
    """

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting Oleeo ingest with max_batch_size={batch_size}")
    ingester = OleeoVacanciesIngest(batch_size=batch_size)
    ingester.do_ingest()


@celery.task(**TASK_KWARGS)
@on_db_disconnect_raise(using="oleeo")
def aggregate_applicant_statistics(
    batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE, initial_vacancy_id=None
):
    """
    Ingest data from OLEEO / R2D2.

    Once the vacancy data is ingested, further work is required, e.g. embedding,
    see `jao_backend.common.tasks` for orchestration tasks.
    """

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting Oleeo ingest with max_batch_size={batch_size}")
    ingester = OleeoApplicantStatisticsAggregator(
        batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
    )
    ingester.do_ingest()


update_vacancies = chain(
    ingest_vacancies.s(), aggregate_applicant_statistics.s(), embed_vacancies.s()
)
"""
Ingest vacancies, and then start embedding.
"""
