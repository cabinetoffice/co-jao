import sys

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

# Admin security settings for development
ADMIN_ALLOWED_IPS = [
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
]

# CSRF settings for Django admin through load balancer
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False  # Don't tie CSRF to sessions for load balancer compatibility
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "http://jao-dev-alb-1122709957.eu-west-2.elb.amazonaws.com",
    "https://jao-dev-alb-1122709957.eu-west-2.elb.amazonaws.com",
    "https://t3k4ooptyi.execute-api.eu-west-2.amazonaws.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Allow CSRF cookies to be set from load balancer
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Session cookie settings
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = BASE_DIR / 'static/webpack-bundles/webpack-stats-dev.json'

# In dev environments default to ollama:
LITELLM_API_BASE = LITELLM_API_BASE or "http://127.0.0.1:11434/api/embed"

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

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
JUPYTER_TOKEN = os.getenv("JAO_BACKEND_JUPYTER_TOKEN", "")
JUPYTER_PORT = os.getenv("JAO_BACKEND_JUPYTER_PORT", 8888)

NOTEBOOK_ARGUMENTS = [
    "--ip=0.0.0.0",
    f"--port={JUPYTER_PORT}",
    "--no-browser",
    f'--IdentityProvider.token="{JUPYTER_TOKEN}"',
    "--IdentityProvider.password_required=false",
]

SHELL_PLUS_JUPYTER_NOTEBOOK_ARGUMENTS = NOTEBOOK_ARGUMENTS
