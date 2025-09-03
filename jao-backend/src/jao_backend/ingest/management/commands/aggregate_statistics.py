import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.log import logging
from jao_backend.common.management.helpers import TaskCommandMixin
from jao_backend.vacancies.models import Vacancy
from jao_backend.oleeo.models import Vacancies
from jao_backend.vacancies.tasks import aggregate_applicant_statistics

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
        parser.add_argument(
            "--initial-vacancy-id",
            type=int,
            default=None,
            help="Initial vacancy ID to start processing from, useful for resuming after a failure",
        )

    def handle(self, *args, **options):
        no_wait = options['no_wait']
        batch_size = options['batch_size']
        initial_vacancy_id = options['initial_vacancy_id']

        max_vacancy_id = getattr(Vacancy.objects.order_by("pk").last(), "pk", 0)
        if not max_vacancy_id:
            sys.exit("No vacancies to aggregate.")

        max_vacancies_id = Vacancies.objects.order_by("pk").last().pk
        if max_vacancy_id != max_vacancies_id:
            # Warn that there are newer vacancies on OLEEO that won't be aggregated
            logger.warning(
                "The maximum vacancy ID in the local database (%s) does not match the maximum vacancy ID in the OLEEO database (%s). Newer vacancies will not be aggregated."
            )

        # Build kwargs for the task
        task_kwargs = {'max_batch_size': batch_size}
        if initial_vacancy_id is not None:
            task_kwargs['initial_vacancy_id'] = initial_vacancy_id

        self.run_task(
            options,
            aggregate_applicant_statistics,
            **task_kwargs
        )