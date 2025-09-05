from celery_singleton import Singleton


class ActiveSingleton(Singleton):
    """
    Singleton task that drops it's lock if the finishes or is terminated
    (when the task is no longer active).
    """

    abstract = True

    TERMINAL_STATES = {"FAILURE", "SUCCESS", "REVOKED", "RETRY"}

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
