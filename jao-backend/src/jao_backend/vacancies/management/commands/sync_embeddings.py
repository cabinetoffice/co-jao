from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from jao_backend.embeddings.service import EmbeddingService
from jao_backend.vacancies.models import Vacancy


class Command(BaseCommand):
    """
    Synchronises embeddings for all vacancies by:
    - Identifying vacancies with no / out of date embeddings
    - Generating fresh embeddings
    - Atomic storage to database per vacancy

    Execution modes:
    - Full sync (default): All vacancies
    - Incremental: Only stale/missing/expired embeddings
    """

    # Temporarily constrain the number of embeddings, once we can ingest from oleeo we
    # can have date based constraints instead, from settings
    MAX_EMBEDDINGS = 1000
    OLDEST_EMBEDDING_AGE = timezone.now() - timedelta(days=30)

    help = "Populate embeddings for vacancies"

    def handle(self, *args, **options):
        """
        Execution flow:
        - Find vacancies without recent embeddings
        - Generate and store embeddings
        - Update sync timestamp
        """

        service = EmbeddingService()
        vacancies = self._get_vacancies_to_sync()

        if not vacancies.exists():
            self.stdout.write("No vacancies to process")
            return

        for vacancy in vacancies:
            self.stdout.write(f"Processing vacancy {vacancy.id}")
            service.create_for_vacancy(vacancy)

    def _get_vacancies_to_sync(self) -> QuerySet:
        vacancies = Vacancy.objects.filter(vacancyembedding__isnull=True).order_by("id")
        # TODO: OLEEO doesn't reflect create_at on vacancy, so we can't limit by date
        count = vacancies.count()
        return vacancies[max(count - self.MAX_EMBEDDINGS, 0) :]
