import sys

from .common import *

try:
    from .local import *
except ImportError:
    pass

DEBUG = True

JAO_BACKEND_TIMEOUT = os.environ.get("JAO_BACKEND_TIMEOUT", 60)

SECRET_KEY = "django-insecure-0+=k_0_cz_8laec^(@6l*$wb(3(^u-=3iy13=$o_$p1vmg*#t0"

ALLOWED_HOSTS = ["*"]

ADMIN_ALLOWED_IPS = [
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
]

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

if DEPLOYMENT_TYPE == "local" and LITELLM_CUSTOM_PROVIDER == "ollama":
    LITELLM_API_BASE = LITELLM_API_BASE or "http://host.docker.internal:11434"

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

try:
    import django_extensions
    if "django_extensions" not in INSTALLED_APPS:
        INSTALLED_APPS += ["django_extensions"]
except ImportError:
    pass

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
