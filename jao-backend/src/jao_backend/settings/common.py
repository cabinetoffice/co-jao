"""
Django settings for JAO Data Engine.

This is a minimal configuration for the data pipeline (ingestion, embedding, clustering).
Web/UI components have been removed.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from jao_backend.common.db.fields import uuidv7
from jao_backend.common.util import is_truthy

ENV = os.environ.get("ENV", "dev").lower()
IS_DEV_ENVIRONMENT = ENV in ["dev", "ci", "local"]

ALLOWED_HOSTS = ['*']

# DEPLOYMENT_TYPE determines which models and embedding backend to use.
# - local:  Ollama backend, public models.
# - aws:    Bedrock backend, proprietary models.
DEPLOYMENT_TYPE = os.environ.get("DEPLOYMENT_TYPE", "local").lower()
if DEPLOYMENT_TYPE not in ["local", "aws"]:
    raise ImproperlyConfigured(
        "DEPLOYMENT_TYPE must be either 'local' or 'aws'. "
        "Current value: {}".format(DEPLOYMENT_TYPE)
    )

LITELLM_CUSTOM_PROVIDER = "ollama" if DEPLOYMENT_TYPE == "local" else "bedrock"

# Note: On bedrock this isn't usually set.
LITELLM_API_BASE = os.environ.get("JAO_BACKEND_LITELLM_API_BASE")

MAX_TOKENS = os.environ.get("MAX_TOKENS", 4000)

JAO_BEDROCK_REGION = "eu-west-2"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "JAO_BACKEND_SECRET_KEY",
    "django-insecure-0+=k_0_cz_8laec^(@6l*$wb(3(^u-=3iy13=$o_$p1vmg*#t0",
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = BASE_DIR.parent

# Data Engine Settings
JAO_BACKEND_VACANCY_EMBED_LIMIT = int(
    os.environ.get("JAO_BACKEND_VACANCY_EMBED_LIMIT", 70_000) or 70_000
)
JAO_BACKEND_VACANCY_EMBED_BATCH_SIZE = int(
    os.environ.get("JAO_BACKEND_VACANCY_EMBED_BATCH_SIZE", 1000)
)
JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE = int(
    os.environ.get("JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE", 50000)
)

# Skills worker HTTP endpoint (replaces Celery)
SKILLS_WORKER_URL = os.environ.get("SKILLS_WORKER_URL", "http://skills-worker:5000")

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # JAO Data Engine apps
    "jao_backend.common",
    "jao_backend.roles",
    "jao_backend.departments",
    "jao_backend.vacancies",
    "jao_backend.application_statistics",
    "jao_backend.embeddings",
    "jao_backend.ingest",
    "jao_backend.oleeo",
    "jao_backend.healthcheck",
    "jao_backend.applicant_text",
    "jao_backend.skills",
]

DEBUG = True

# Use the pytest-django plugin to run tests
TEST_RUNNER = "jao_backend.settings.tests.runner.PytestTestRunner"

# Chat models, for lookup by LITELLM_CUSTOM_PROVIDER.
CHAT_MODEL_OPTIONS = {
    "ollama": "mistral:7b",
    "bedrock": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
}

LITELLM_COMPLETION_MODEL = CHAT_MODEL_OPTIONS[LITELLM_CUSTOM_PROVIDER]

# Text embedding models, for lookup by LITELLM_CUSTOM_PROVIDER.
TEXT_EMBEDDING_MODEL_OPTIONS = {
    "ollama": "nomic-embed-text:latest",
    "bedrock": "bedrock/amazon.titan-embed-text-v2:0",
}

AWS_TAGS_FOR_EMBEDDING = {"project": "jao", "environment": ENV}

# Concatenated job title and responsibilities embedding tag
# Do not change uuids once assigned!
EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID = uuidv7(
    hex="0196a2a0-61b9-79e2-9ef7-9988b475dda3"
)

EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_MODEL = os.environ.get(
    "JAO_EMBEDDER_SUMMARY_RESPONSIBILITIES",
    TEXT_EMBEDDING_MODEL_OPTIONS[LITELLM_CUSTOM_PROVIDER],
)

# Tag definitions here are synced to the database in `EmbeddingTag.get_configured_tags`
EMBEDDING_TAGS = {
    EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID: {
        "uuid": EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID,
        "name": "job-title-responsibilities",
        "description": "Job title and responsibilities concatenated",
        "model": EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_MODEL,
        "version": 1,
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database
DATABASES = {
    "default": dj_database_url.config(env="JAO_BACKEND_DATABASE_URL"),
}

JAO_BACKEND_ENABLE_OLEEO = is_truthy(
    os.environ.get("JAO_BACKEND_ENABLE_OLEEO", "false")
)
if JAO_BACKEND_ENABLE_OLEEO:
    DATABASES["oleeo_upstream"] = dj_database_url.config(env="JAO_BACKEND_OLEEO_DATABASE_URL")
    DATABASE_ROUTERS = ["jao_backend.common.routers.router.OleeoRouter"]

# Session engine
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# Static files (minimal config for admin)
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "jao_backend": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# S3 configuration
S3_ENDPOINTS_FROM_AWS_ENV = os.getenv("S3_ENDPOINTS_FROM_AWS_ENV", "false").lower() in (
    "true",
    "1",
    "yes",
)
S3_ENDPOINTS = {
    "default": None,  # AWS configured credentials
}
