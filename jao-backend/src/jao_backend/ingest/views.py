from celery.result import AsyncResult
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.shortcuts import render
from django.views import View

from .forms import IngestForm
from jao_backend.vacancies.tasks import ingest_vacancies


class IngestStatusView(LoginRequiredMixin, View):
    template_name = "ingest/ingest_status.html"

    def get_task_status(self):
        """
        Check if the singleton ingest task is running.
        Returns task_id if running, None otherwise.
        """
        # Get Celery app from your task
        app = ingest_vacancies.app

        # Create inspector to look at active tasks
        inspector = app.control.inspect()

        # Get all active tasks across all workers
        active_tasks = inspector.active() or {}

        # Look for any ingest task in the active tasks
        for worker, tasks in active_tasks.items():
            for task in tasks:
                if (
                    task.get("name") == "jao_internal.ingest.tasks.ingest"
                ):  # Update with actual task path
                    return task.get("id")

        return None

    def get(self, request):
        # Check if task is running
        task_id = self.get_task_status()

        # Initialize context with a new form
        context = {
            "form": IngestForm(),
            "task_id": task_id,
            "task_running": task_id is not None,
            "task_result": None,
        }

        # If we have a task_id, try to get its result
        if task_id:
            result = AsyncResult(task_id)
            if result.ready():
                context["task_result"] = result.result
                context["task_status"] = "completed"
            else:
                context["task_status"] = "running"

        return render(request, self.template_name, context)

    def post(self, request):
        form = IngestForm(request.POST)

        # Check if task is already running
        task_id = self.get_task_status()
        if task_id:
            messages.warning(request, "An ingest task is already running.")
            return redirect("ingest_status")

        if form.is_valid():
            batch_size = (
                form.cleaned_data.get("max_batch_size")
                or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
            )
            task = ingest_vacancies.delay(batch_size=batch_size)
            messages.success(request, f"Ingest task started with ID: {task.id}")
            return redirect("ingest_status")

        return render(request, self.template_name, {"form": form})
