from celery.utils.log import get_task_logger
from celery_singleton import Singleton
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from jao_backend.common.celery import app as celery
from jao_backend.ingest.ingester.oleeo_ingest import OleeoIngest

logger = get_task_logger(__name__)


@celery.task(base=Singleton)
def ingest(max_batch_size=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE):
    """
    Ingest data from OLEEO / R2D2.
    """

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    logger.info(f"Starting Oleeo ingest with max_batch_size={max_batch_size}")
    ingester = OleeoIngest(max_batch_size=max_batch_size)
    ingester.do_ingest()
