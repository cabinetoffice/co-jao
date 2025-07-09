from .common import *

DEBUG = False

WEBPACK_LOADER["DEFAULT"]["STATS_FILE"] = (
    BASE_DIR / "static/webpack-bundles/webpack-stats-prod.json"
)

SESSION_COOKIE_SECURE = True

# On production and production-like systems use bedrock based embedders
EMBEDDING_TAGS[EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID].update(
    {
        "model": "bedrock/amazon.titan-embed-text-v1",
    }
)

LITELLM_CUSTOM_PROVIDER = LITELLM_CUSTOM_PROVIDER or "bedrock"
