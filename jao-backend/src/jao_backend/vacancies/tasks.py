"""
Data pipeline functions for vacancy processing.

These functions perform the actual work of the data pipeline:
- Ingesting vacancies from OLEEO
- Aggregating applicant statistics
- Embedding vacancies
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from jao_backend.vacancies.embed import embed_vacancy
from jao_backend.vacancies.models import Vacancy
from jao_backend.ingest.ingester.ingest_vacancies import OleeoVacanciesIngest
from jao_backend.ingest.ingester.ingest_applicant_text import ApplicantTextIngest
from jao_backend.ingest.ingester.ingest_aggregated_applicants import (
    OleeoApplicantStatisticsAggregator,
    OleeoApplicantRegionAggregator
)

logger = logging.getLogger(__name__)


def embed_vacancies(limit=None):
    if limit is None:
        limit = settings.JAO_BACKEND_VACANCY_EMBED_LIMIT

    vacancies = (
        Vacancy.objects.filter(is_deleted=False)
        .order_by("-id")
        .requires_embedding(limit=limit)
    )

    total_embedded = 0
    logger.info(
        "Embed vacancies. limit=%s, vacancies to embed: %s",
        limit,
        len(vacancies),
    )
    try:
        for vacancy in vacancies:
            if not vacancy.get_requires_embedding():
                logger.info("Vacancy %s already embedded, skipping.", vacancy.id)
                continue

            embed_vacancy(vacancy)
            total_embedded += 1
    finally:
        logger.info("Embedded %s/%s vacancies", total_embedded, len(vacancies))

    return total_embedded


def ingest_vacancies(batch_size=None):
    if batch_size is None:
        batch_size = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting Oleeo ingest with max_batch_size={batch_size}")
    ingester = OleeoVacanciesIngest(batch_size=batch_size)
    ingester.do_ingest()


def aggregate_applicant_statistics(batch_size=None, initial_vacancy_id=None):
    if batch_size is None:
        batch_size = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting applicant statistics aggregation with max_batch_size={batch_size}")
    ingester = OleeoApplicantStatisticsAggregator(
        batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
    )
    ingester.do_ingest()


def aggregate_applicant_regions(batch_size=None, initial_vacancy_id=None):
    if batch_size is None:
        batch_size = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("OLEEO integration is disabled, cannot aggregate regions.")
        raise ImproperlyConfigured("OLEEO integration is not enabled")

    logger.info(f"Starting Oleeo applicant region aggregation with max_batch_size={batch_size}")

    aggregator = OleeoApplicantRegionAggregator(
        batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
    )
    aggregator.do_ingest()
    logger.info("Oleeo applicant region aggregation finished successfully.")


def ingest_applicant_text(batch_size=None, initial_vacancy_id=None):
    if batch_size is None:
        batch_size = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("OLEEO integration is disabled, cannot ingest applicant text.")
        raise ImproperlyConfigured("OLEEO integration is not enabled")

    logger.info(f"Starting applicant text ingestion with max_batch_size={batch_size}")

    ingester = ApplicantTextIngest(
        batch_size=batch_size, initial_vacancy_id=initial_vacancy_id
    )
    ingester.do_ingest()
    logger.info("Applicant text ingestion finished successfully.")
