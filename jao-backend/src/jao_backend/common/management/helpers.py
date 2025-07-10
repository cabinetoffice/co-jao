from django.conf import settings


class TaskCommandMixin:
    """
    Mixin to with convenience functions to wrap a celery task
    """

    celery_only = False
    """Commands that use celery canvas should set this to True."""

    def add_arguments(self, parser):
        if not self.celery_only:
            parser.add_argument(
                "--local",
                action="store_true",
                help="Validate the data without ingesting it",
            )

        parser.add_argument(
            "--no-wait",
            action="store_true",
            help="Do not wait for the ingest task to complete; run it asynchronously",
        )

    def run_task(self, options, task, *args, **kwargs):
        """
        Run the specified task with the provided arguments.

        (Will call as a function if local is True)
        """
        if options["local"]:
            # This option is for validating the ingester, and running locally.
            # In this mode, it's possible to ingest from a file, this wouldn't
            # be possible in production where the the actual ingest runs in a celery
            # worker, which may not be the same machine as the one running the command.
            if not settings.IS_DEV_ENVIRONMENT:
                raise ValueError(
                    "The --local flag can only be used in development mode."
                )

            return task(*args, **kwargs)
        else:
            result = task.delay(*args, **kwargs)
            self.stdout.write(f"{task.__name__} {result.id} started.")  # noqa

            if not options["no_wait"]:
                result.get()
