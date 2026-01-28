from .common import *

INSTALLED_APPS.append("jao_backend.oleeo.tests")

TEST_TAG_ID = uuidv7(hex="0196a4fe-4e54-77de-9ff1-e13291404e5a")
TEST_TAG_MODEL = os.environ.get(
    "JAO_EMBEDDER_TEST_TAG", "sentence-transformers/all-MiniLM-L6-v2"
)

EMBEDDING_TAGS = {
    **EMBEDDING_TAGS,
    TEST_TAG_ID: {
        "uuid": TEST_TAG_ID,
        "name": "test-tag",
        "description": "Description for Test Tag",
        "model": TEST_TAG_MODEL,
        "version": 1,
    },
}

EMBEDDING_TAGS[EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID].update(
    {
        "model": TEST_TAG_MODEL,
    }
)

DEFAULT_TEST_DATABASE_NAME = "postgresql:///jao-backend"
DEFAULT_TEST_OLEEO_DATABASE_NAME = "postgresql:///jao-backend-oleeo"

DATABASES = {
    "default": dj_database_url.config(
        env="JAO_TEST_BACKEND_DATABASE_URL", default=DEFAULT_TEST_DATABASE_NAME
    ),
}

if JAO_BACKEND_ENABLE_OLEEO:
    DATABASES["oleeo"] = dj_database_url.config(
        env="JAO_TEST_BACKEND_OLEEO_DATABASE_URL", default="sqlite://:memory:"
    )
    DATABASE_ROUTERS = ["jao_backend.common.routers.router.OleeoRouter"]
