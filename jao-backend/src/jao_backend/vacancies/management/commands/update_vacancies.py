import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.log import logging

from jao_backend.common.management.helpers import TaskCommandMixin
from jao_backend.vacancies.tasks import update_vacancies

logger = logging.getLogger(__name__)


class Command(TaskCommandMixin, BaseCommand):
    help = "Update vacancies (ingest and then embed), this uses the defaults."
    celery_only = True

    def handle(self, *args, **options):
        """
        To be sparing with memory, and IO this divides the file into chunks and
        then processes them.

        This means we won't need as large instances when running on AWS, and
        is usefully locally when we run LLMs that use a lot of memory.
        """
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO ingest is disabled")
            raise ValueError("OLEEO ingest is not enabled")

        super().run_task(options, update_vacancies)
