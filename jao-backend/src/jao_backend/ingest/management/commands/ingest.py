from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.log import logging

from jao_backend.ingest.tasks import ingest as ingest_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest data from OLEEO database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--local",
            action="store_true",
            help="Validate the data without ingesting it",
        )

        parser.add_argument(
            "--no-wait",
            action="store_true",
            help="Do not wait for the ingest task to complete; run it asynchronously",
        )

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
            logger.error("OLEEO ingest is disabled")
            raise ValueError("OLEEO ingest is not enabled")

        max_batch_size = (
            options["batch_size"] or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
        )
        if options["local"]:
            # This option is for validating the ingester, and running locally.
            # In this mode, it's possible to ingest from a file, this wouldn't
            # be possible in production where the the actual ingest runs in a celery
            # worker, which may not be the same machine as the one running the command.
            if not settings.IS_DEV_ENVIRONMENT:
                raise ValueError(
                    "The --local flag can only be used in development mode."
                )

            ingest_task(max_batch_size=max_batch_size)
        else:
            ingest_result = ingest_task.delay(max_batch_size=max_batch_size)
            self.stdout.write(f"Ingest {ingest_result.id} task started.")

            if not options["no_wait"]:
                ingest_result.get()
