import socket

from jao_web.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# A larger timeout is used to allow
JAO_BACKEND_TIMEOUT = float(os.getenv("JAO_BACKEND_TIMEOUT", 15))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-0+=k_0_cz_8laec^(@6l*$wb(3(^u-=3iy13=$o_$p1vmg*#t0"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = BASE_DIR / 'static/webpack-bundles/webpack-stats-dev.json'


def get_docker_host_ip():
    """Get the host machine's IP address from inside the Docker container."""
    try:
        # When running in Docker, this will get the IP of the host machine
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())

        # Get all IP addresses that aren't localhost
        docker_ips = [ip[:-1] + "1" for ip in ips if ip != "127.0.0.1"]
        return docker_ips
    except socket.gaierror:
        return []


def get_internal_ip(default):
    return os.environ.get("INTERNAL_IPS", f"{default}").replace(" ", "").split(",")


try:
    import debug_toolbar

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = get_internal_ip("127.0.0.1") + get_docker_host_ip()
except ImportError:
    print("No debug toolbar")
    pass

try:
    from .local import *
except ImportError:
    pass
