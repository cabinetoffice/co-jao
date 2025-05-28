import sys

from django.core.exceptions import ImproperlyConfigured

from .common import *

try:
    from .local import *
except ImportError:
    pass

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# A larger timeout is used to allow
JAO_BACKEND_TIMEOUT = os.environ.get("JAO_BACKEND_TIMEOUT", 15)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-0+=k_0_cz_8laec^(@6l*$wb(3(^u-=3iy13=$o_$p1vmg*#t0"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = BASE_DIR / 'static/webpack-bundles/webpack-stats-dev.json'

# In dev environments default to ollama:
LITELLM_API_BASE = LITELLM_API_BASE or "http://127.0.0.1:11434/api/embed"
LITELLM_CUSTOM_PROVIDER = LITELLM_CUSTOM_PROVIDER or "ollama"

try:
    import debug_toolbar

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = (
        os.environ.get("INTERNAL_IPS", "127.0.0.1").replace(" ", "").split(",")
    )
except ImportError:
    print("No debug toolbar", file=sys.stderr)
    pass

MINIO_URL = os.getenv("MINIO_URL")
MINIO_ACCESS_KEY_ID = os.getenv("MINIO_ACCESS_KEY_ID")
MINIO_SECRET_ACCESS_KEY = os.getenv("MINIO_SECRET_ACCESS_KEY")

if MINIO_URL:
    if not all([MINIO_ACCESS_KEY_ID, MINIO_SECRET_ACCESS_KEY]):
        raise ImproperlyConfigured(
            "MINIO_URL is set, MINIO_ACCESS_KEY_ID and MINIO_SECRET_ACCESS_KEY also need to be set."
        )

    S3_ENDPOINTS.update(
        {
            "minio": {
                "endpoint_url": MINIO_URL,
                "aws_access_key_id": MINIO_ACCESS_KEY_ID,
                "aws_secret_access_key": MINIO_SECRET_ACCESS_KEY,
                "config": {
                    "signature_version": "s3v4",
                }
            }
        }
    )

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
JUPYTER_TOKEN = os.getenv("JAO_BACKEND_JUPYTER_TOKEN", "")
JUPYTER_PORT = os.getenv("JAO_BACKEND_JUPYTER_PORT", 8888)

NOTEBOOK_ARGUMENTS = [
    '--ip=0.0.0.0',
    f'--port={JUPYTER_PORT}',
    '--no-browser',
    f'--IdentityProvider.token="{JUPYTER_TOKEN}"',
    '--IdentityProvider.password_required=false'
]

SHELL_PLUS_JUPYTER_NOTEBOOK_ARGUMENTS = NOTEBOOK_ARGUMENTS
