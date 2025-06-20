"""
WSGI config for job_advert_optimiser project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

import dotenv
from django.core.wsgi import get_wsgi_application

# Only load .env file if it exists (for local development)
try:
    dotenv.load_dotenv(dotenv.find_dotenv())
except Exception:
    # Ignore errors if .env file cannot be loaded (e.g., in containerized environments)
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jao_backend.settings.dev")

application = get_wsgi_application()
