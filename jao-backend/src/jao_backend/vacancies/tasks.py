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
from jao_backend.ingest.ingester.ingest_applicant_text import ApplicantTextIngest
from jao_backend.ingest.ingester.ingest_aggregated_applicants import (
    OleeoApplicantStatisticsAggregator,
    OleeoApplicantRegionAggregator
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
@on_db_disconnect_raise(using="oleeo_upstream")
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
@on_db_disconnect_raise(using="oleeo_upstream")
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
@on_db_disconnect_raise(using="oleeo_upstream")
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

@celery.task(**TASK_KWARGS)
@on_db_disconnect_raise(using="oleeo_upstream")
def aggregate_applicant_regions(batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE, initial_vacancy_id=None):
    """
    Aggregates applicant region counts from the Oleeo database using the
    specialized OleeoApplicantRegionAggregator.

    This task reads applicant postcodes, maps them to regions via a CSV lookup,
    counts applicants per region for each vacancy, and stores the results
    in the AggregatedApplicationCount table.
    """
    logger = get_task_logger(__name__)

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("OLEEO integration is disabled, cannot aggregate regions.")
        raise ImproperlyConfigured("OLEEO integration is not enabled")

    logger.info(f"Starting Oleeo applicant region aggregation with max_batch_size={batch_size}")

    try:
        aggregator = OleeoApplicantRegionAggregator(
            batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
        )
        aggregator.do_ingest()
        logger.info("Oleeo applicant region aggregation finished successfully.")
    except Exception as e:
        logger.error(f"Error during applicant region aggregation: {e}", exc_info=True)

        raise

@celery.task(**TASK_KWARGS)
@on_db_disconnect_raise(using="oleeo_upstream")
def ingest_applicant_text(batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE, initial_vacancy_id=None):
    """
    Ingests and aggregates applicant free-text fields from the Oleeo database
    using the specialized ApplicantTextIngest class.

    This task performs two steps:
    1. Ingests raw text (personal statement, employment history, skill experience) into the
       ApplicationText table.
    2. Aggregates all text for each vacancy into the
       VacancyTextAggregate table.
    """
    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("OLEEO integration is disabled, cannot ingest applicant text.")
        raise ImproperlyConfigured("OLEEO integration is not enabled")

    logger.info(f"Starting applicant text ingestion with max_batch_size={batch_size}")

    try:
        ingester = ApplicantTextIngest(
            batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
        )
        ingester.do_ingest()
        logger.info("Applicant text ingestion finished successfully.")
    except Exception as e:
        logger.error(f"Error during applicant text ingestion: {e}", exc_info=True)
        raise

update_vacancies = chain(
    # Immutable signatures (.si) so each task keeps its own defaults instead of receiving
    # the previous task's return value as its first positional arg (batch_size).
    ingest_vacancies.si(), aggregate_applicant_statistics.si(), aggregate_applicant_regions.si(), ingest_applicant_text.si(), embed_vacancies.si()
)
"""
Ingest vacancies, and then start embedding.
"""
