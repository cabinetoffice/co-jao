from celery import current_app as celery


def are_tasks_running(*task_names):
    """
    Check if specified tasks are currently running.

    Args:
        *task_names: Variable number of task names to check

    Returns:
        List of bools indicating if each task is running (same order as input)
    """
    if not task_names:
        return []

    # Get all currently active tasks
    active_tasks = celery.control.inspect().active()
    running_tasks = set()

    if active_tasks:
        for worker, tasks in active_tasks.items():
            for task in tasks:
                running_tasks.add(task["name"])

    # Return boolean for each task name
    return [task_name in running_tasks for task_name in task_names]


def is_task_running(task_name):
    """
    Check if a single task is currently running.

    Args:
        task_name: Full task name to check

    Returns:
        bool: True if task is running, False otherwise
    """
    return are_tasks_running(task_name)[0]
