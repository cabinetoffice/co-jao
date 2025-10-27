import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils.log import logging
from jao_backend.common.management.helpers import TaskCommandMixin
from jao_backend.vacancies.models import Vacancy
from jao_backend.vacancies.tasks import aggregate_applicant_regions 

logger = logging.getLogger(__name__)


class Command(TaskCommandMixin, BaseCommand):

    help = "Aggregate applicant region counts from OLEEO database."

    def add_arguments(self, parser):
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
        batch_size = options["batch_size"]
        initial_vacancy_id = options["initial_vacancy_id"]

        if not Vacancy.objects.exists():
            sys.exit("No vacancies found in the local database to aggregate region data for.")

        task_kwargs = {"batch_size": batch_size}
        if initial_vacancy_id is not None:
            task_kwargs["initial_vacancy_id"] = initial_vacancy_id


        connections.close_all()

        self.run_task(options, aggregate_applicant_regions, **task_kwargs)