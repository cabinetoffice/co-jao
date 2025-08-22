from time import sleep

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

    def wait_for_vacancies(self):
        while True:
            if not Vacancy.objects.exists():
                sleep(60)
                continue
            max_vacancy_id = Vacancy.objects.order_by("pk").last().pk
            max_vacancies_id = Vacancies.objects.order_by("pk").last().pk
            if max_vacancy_id == max_vacancies_id:
                break
            logger.info("max vacancy_id: %s, %s", max_vacancy_id, max_vacancies_id)
            sleep(60)

    def handle(self, *args, initial_vacancy_id, batch_size, no_wait, **options):
        if not no_wait:
            self.wait_for_vacancies()

        self.run_task(
            options, aggregate_applicant_statistics, max_batch_size=batch_size
        )
