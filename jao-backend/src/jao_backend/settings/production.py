from .common import *
import os

DEBUG = False

# Production security settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set in production")

# Restrict allowed hosts in production
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("DJANGO_ALLOWED_HOSTS environment variable must be set in production")

# Admin IP restrictions for production
ADMIN_ALLOWED_IPS = os.environ.get('ADMIN_ALLOWED_IPS', '').split(',') if os.environ.get('ADMIN_ALLOWED_IPS') else []

WEBPACK_LOADER["DEFAULT"]["STATS_FILE"] = (
    BASE_DIR / "static/webpack-bundles/webpack-stats-prod.json"
)

# Enhanced security settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Security headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Admin security - restrict to specific IPs in production
ADMIN_ALLOWED_IPS = os.environ.get('ADMIN_ALLOWED_IPS', '').split(',')
if ADMIN_ALLOWED_IPS == ['']:
    ADMIN_ALLOWED_IPS = []

# Admin session timeout (shorter in production)
ADMIN_SESSION_TIMEOUT = 1800  # 30 minutes

# Force HTTPS for admin
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# On production and production-like systems use bedrock based embedders
EMBEDDING_TAGS[EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID].update(
    {
        "model": "bedrock/amazon.titan-embed-text-v1",
    }
)

LITELLM_CUSTOM_PROVIDER = LITELLM_CUSTOM_PROVIDER or "bedrock"
