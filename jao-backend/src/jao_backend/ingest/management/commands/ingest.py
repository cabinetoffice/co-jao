from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.log import logging

from jao_backend.common.management.helpers import TaskCommandMixin
from jao_backend.vacancies.tasks import ingest_vacancies

logger = logging.getLogger(__name__)


class Command(TaskCommandMixin, BaseCommand):
    help = "Ingest data from OLEEO database."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE,
            help="Maximum batch size for processing records in chunks",
        )

    def handle(self, *args, **options):
        """
        To be sparing with memory, and IO this divides the file into chunks and
        then processes them.

        This means we won't need as large instances when running on AWS, and
        is usefully locally when we run LLMs that use a lot of memory.
        """
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled")
            raise ValueError("OLEEO integration is not enabled")

        max_batch_size = (
            options["batch_size"] or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
        )
        self.run_task(options, ingest_vacancies, max_batch_size=max_batch_size)
