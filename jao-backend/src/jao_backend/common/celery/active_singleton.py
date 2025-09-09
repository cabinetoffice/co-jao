import logging

from celery_singleton import Singleton


logger = logging.getLogger(__name__)

class ActiveSingleton(Singleton):
    """
    Singleton task that drops it's lock if the finishes or is terminated
    (when the task is no longer active).
    """

    abstract = True

    TERMINAL_STATES = {"FAILURE", "SUCCESS", "REVOKED"}

    def get_existing_task_id(self, lock):
        """
        Checks for for the active task ID.
        """
        existing_task_id = super().get_existing_task_id(lock)

        if not existing_task_id:
            return None

        result = self.AsyncResult(existing_task_id)
        if result.state in self.TERMINAL_STATES:
            self.unlock(lock)
            return None

        return existing_task_id

    def retry(self, *args, **kwargs):
        # See https://github.com/steinitzu/celery-singleton/pull/26
        self.release_lock(task_args=self.request.args, task_kwargs=self.request.kwargs)
        return super().retry(*args, **kwargs)

