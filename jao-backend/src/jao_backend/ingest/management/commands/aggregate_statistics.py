import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from jao_backend.vacancies.models import Vacancy
from jao_backend.vacancies.tasks import aggregate_applicant_statistics

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Aggregate applicant D&I statistics from OLEEO database."

    def add_arguments(self, parser):
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
            help="Initial vacancy ID to start processing from",
        )

    def handle(self, *args, **options):
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            self.stderr.write("OLEEO integration is disabled")
            return

        if not Vacancy.objects.exists():
            self.stderr.write("No vacancies to aggregate.")
            return

        batch_size = options["batch_size"]
        initial_vacancy_id = options["initial_vacancy_id"]

        self.stdout.write(f"Starting statistics aggregation with batch_size={batch_size}")
        aggregate_applicant_statistics(
            batch_size=batch_size,
            initial_vacancy_id=initial_vacancy_id
        )
        self.stdout.write(self.style.SUCCESS("Statistics aggregation complete"))
