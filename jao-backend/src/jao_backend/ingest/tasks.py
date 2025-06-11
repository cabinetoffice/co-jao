from celery_singleton import Singleton
from celery.utils.log import get_task_logger

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from jao_backend.common.celery import app as celery
from jao_backend.ingest.ingester.oleeo_ingest import OleeoIngest

logger = get_task_logger(__name__)


@celery.task(base=Singleton)
def ingest():
    """
    Download a Parquet file from S3 and process it.

    Args:
        s3_url: The S3 URL of the Parquet file to download
        download_dir: The directory to download the file to. If None then tmpdir is used.
    """

    if not settings.JAO_BACKEND_ENABLE_OLEEO:
        logger.error("Oleeo ingest is disabled")
        raise ImproperlyConfigured("Oleeo ingest is not enabled")

    ingester = OleeoIngest()
    ingester.update()
