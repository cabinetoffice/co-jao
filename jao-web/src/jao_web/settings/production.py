from jao_web.settings.common import *

DEBUG = False

WEBPACK_LOADER["DEFAULT"]["STATS_FILE"] = (
    BASE_DIR / "static/webpack-bundles/webpack-stats-prod.json"
)

SESSION_COOKIE_SECURE = True

try:
    from .local import *
except ImportError:
    pass
