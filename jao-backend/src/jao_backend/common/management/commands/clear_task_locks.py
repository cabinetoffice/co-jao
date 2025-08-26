from celery_singleton import clear_locks
from django.core.management import BaseCommand

from jao_backend.common.celery import app as celery_app


class Command(BaseCommand):
    help = 'Clear all singleton task locks held in Redis/Elasticache.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-y', '--yes',
            action='store_true',
            help='Skip confirmation prompt and proceed directly',
        )

    def handle(self, *args, **options):
        """
        In rare circumstances the celery-singleton locks are not released, remove them
        with this.

        Using this while tasks are running may cause concurrency issues if a task is
        still running that expects to run as a singleton.

        See: https://github.com/steinitzu/celery-singleton?tab=readme-ov-file#handling-deadlocks
        """
        if not options['yes']:
            confirm = input("Clear all task locks? [y/N]: ")
            if confirm.lower() not in ['y', 'yes']:
                return "Cancelled."

        clear_locks(celery_app)
        self.stdout.write("Task locks cleared.")