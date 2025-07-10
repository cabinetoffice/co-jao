import dotenv
import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
env = os.environ.get("ENV", "common")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"jao_backend.settings.{env}")

dotenv.load_dotenv()

# Create a Celery instance and set the broker and result backend.
app = Celery("jao_backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
