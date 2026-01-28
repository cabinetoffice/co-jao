import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from jao_backend.vacancies.tasks import ingest_vacancies

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest vacancy data from OLEEO database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE,
            help="Maximum batch size for processing records in chunks",
        )

    def handle(self, *args, **options):
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            self.stderr.write("OLEEO integration is disabled")
            return

        batch_size = options["batch_size"]
        self.stdout.write(f"Starting vacancy ingest with batch_size={batch_size}")
        ingest_vacancies(batch_size=batch_size)
        self.stdout.write(self.style.SUCCESS("Vacancy ingest complete"))
