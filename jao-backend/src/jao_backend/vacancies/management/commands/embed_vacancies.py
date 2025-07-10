from django.conf import settings
from django.core.management import BaseCommand

from jao_backend.common.management.helpers import TaskCommandMixin
from jao_backend.vacancies.tasks import embed_vacancies


class Command(TaskCommandMixin, BaseCommand):
    help = "Embed vacancies"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--limit",
            type=int,
            default=settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
            help="Limit the number of vacancies to embed (maximum is in settings.JAO_BACKEND_VACANCY_EMBED_LIMIT",
        )

    def handle(self, *args, **options):
        """
        Embeds vacancies using the configured embedding service.

        This command will process vacancies in batches, embedding them
        until the specified limit is reached.
        """
        limit = options["limit"]
        if limit > settings.JAO_BACKEND_VACANCY_EMBED_LIMIT:
            self.stderr.write(
                f"Limit {limit} exceeds maximum allowed {settings.JAO_BACKEND_VACANCY_EMBED_LIMIT}. Using maximum."
            )
            limit = settings.JAO_BACKEND_VACANCY_EMBED_LIMIT

        super().run_task(options, embed_vacancies, limit=limit)
