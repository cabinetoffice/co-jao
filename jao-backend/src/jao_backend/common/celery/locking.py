from logging import getLogger

from celery import current_app
from celery_singleton.config import Config
from celery_singleton.backends import get_backend

from jao_backend.common.celery.monitoring import is_task_running

logger = getLogger(__name__)


def clear_stale_lock(task_name):
    """
    Clear a singleton lock if the task is not currently running.

    Args:
        task_name: Full task name (e.g., 'jao_backend.vacancies.tasks.ingest_vacancies')
    """
    if is_task_running(task_name):
        logger.info(f"Task {task_name} is currently running, lock not cleared")
        return f"Task {task_name} is currently running, lock not cleared"

    app = current_app
    config = Config(app)
    backend = get_backend(config)

    try:
        lock_key = f"SINGLETONLOCK_{task_name}"
        backend.clear(lock_key)
        logger.info(f"Cleared stale singleton lock for task: {task_name}")
        return f"Lock cleared for {task_name}"
    except Exception as e:
        logger.error(f"Failed to clear lock for {task_name}: {e}")
        return f"Failed to clear lock: {e}"
