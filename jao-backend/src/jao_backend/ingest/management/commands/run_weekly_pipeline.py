import logging

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the complete weekly data ingestion pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE,
            help="Batch size for ingestion steps",
        )
        parser.add_argument(
            "--embed-limit",
            type=int,
            default=settings.JAO_BACKEND_VACANCY_EMBED_LIMIT,
            help="Limit for vacancy embedding",
        )
        parser.add_argument(
            "--skip-ingest",
            action="store_true",
            help="Skip vacancy ingestion step",
        )
        parser.add_argument(
            "--skip-statistics",
            action="store_true",
            help="Skip statistics aggregation step",
        )
        parser.add_argument(
            "--skip-regions",
            action="store_true",
            help="Skip region aggregation step",
        )
        parser.add_argument(
            "--skip-applicant-text",
            action="store_true",
            help="Skip applicant text ingestion step",
        )
        parser.add_argument(
            "--skip-skills",
            action="store_true",
            help="Skip skills extraction step",
        )
        parser.add_argument(
            "--skip-clustering",
            action="store_true",
            help="Skip skills clustering step",
        )
        parser.add_argument(
            "--skip-embedding",
            action="store_true",
            help="Skip embedding generation step",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        embed_limit = options["embed_limit"]

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("JAO Data Engine - Weekly Pipeline"))
        self.stdout.write(self.style.WARNING("=" * 60))

        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            self.stderr.write(self.style.ERROR("OLEEO integration is disabled. Aborting."))
            return

        steps = [
            ("ingest", "Ingesting vacancies from OLEEO", {"batch_size": batch_size}),
            ("aggregate_statistics", "Aggregating applicant statistics", {"batch_size": batch_size}),
            ("aggregate_regions", "Aggregating applicant regions", {"batch_size": batch_size}),
            ("ingest_applicant_text", "Ingesting applicant text", {"batch_size": batch_size}),
            ("extract_skills", "Extracting skills from applicant text", {}),
            ("cluster_skills", "Clustering skills", {"cluster": True, "name": True}),
            ("embed_vacancies", "Generating vacancy embeddings", {"limit": embed_limit}),
        ]

        skip_flags = {
            "ingest": options["skip_ingest"],
            "aggregate_statistics": options["skip_statistics"],
            "aggregate_regions": options["skip_regions"],
            "ingest_applicant_text": options["skip_applicant_text"],
            "extract_skills": options["skip_skills"],
            "cluster_skills": options["skip_clustering"],
            "embed_vacancies": options["skip_embedding"],
        }

        for command_name, description, command_options in steps:
            if skip_flags.get(command_name):
                self.stdout.write(f"Skipping: {description}")
                continue

            self.stdout.write("")
            self.stdout.write(self.style.NOTICE(f"Step: {description}"))
            self.stdout.write("-" * 40)

            try:
                call_command(command_name, **command_options)
                self.stdout.write(self.style.SUCCESS(f"Completed: {description}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed: {description}"))
                self.stderr.write(str(e))
                raise

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Pipeline complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
