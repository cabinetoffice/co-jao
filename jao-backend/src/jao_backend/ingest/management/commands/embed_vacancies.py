from django.conf import settings
from django.core.management import BaseCommand

from jao_backend.vacancies.tasks import embed_vacancies


class Command(BaseCommand):
    help = "Generate embeddings for vacancies that need them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
            help="Limit the number of vacancies to embed",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit > settings.JAO_BACKEND_VACANCY_EMBED_LIMIT:
            self.stderr.write(
                f"Limit {limit} exceeds maximum {settings.JAO_BACKEND_VACANCY_EMBED_LIMIT}. Using maximum."
            )
            limit = settings.JAO_BACKEND_VACANCY_EMBED_LIMIT

        self.stdout.write(f"Starting vacancy embedding with limit={limit}")
        total = embed_vacancies(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Embedded {total} vacancies"))
