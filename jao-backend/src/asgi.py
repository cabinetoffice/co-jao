"""
ASGI config for job_advert_optimiser project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

import dotenv
from django.core.asgi import get_asgi_application

# Only load .env file if it exists (for local development)
try:
    dotenv.load_dotenv(dotenv.find_dotenv())
except Exception:
    # Ignore errors if .env file cannot be loaded (e.g., in containerized environments)
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jao_backend.settings.dev")

application = get_asgi_application()
