import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils.log import logging
from jao_backend.common.management.helpers import TaskCommandMixin 

from jao_backend.vacancies.tasks import ingest_applicant_text

logger = logging.getLogger(__name__)


class Command(TaskCommandMixin, BaseCommand):
    """
    This command ingests and aggregates applicant free-text fields from Oleeo
    by queueing the corresponding Celery task.
    """
    help = "Ingests and aggregates applicant free-text fields from Oleeo."

    def add_arguments(self, parser):
        """
        This method adds the arguments, matching the style of other ingesters.
        """
        super().add_arguments(parser)
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE,
            help="Maximum batch size for processing records in chunks",
        )
        parser.add_argument(
            "--initial-vacancy-id",
            type=int,
            default=None,
            help="Initial vacancy ID to start processing from, useful for resuming after a failure",
        )

    def handle(self, *args, **options):
        """
        The main handler that passes arguments to the Celery task.
        """
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled, cannot run ingest.")
            raise ValueError("OLEEO integration is not enabled")

        batch_size = options["batch_size"]
        initial_vacancy_id = options["initial_vacancy_id"]

        task_kwargs = {"batch_size": batch_size}
        if initial_vacancy_id is not None:
            task_kwargs["initial_vacancy_id"] = initial_vacancy_id

        connections.close_all()

        self.run_task(options, ingest_applicant_text, **task_kwargs)

        self.stdout.write(self.style.SUCCESS(
            "Successfully queued applicant text ingest task."
        ))