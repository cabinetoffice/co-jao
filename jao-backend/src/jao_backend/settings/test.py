from .common import *

INSTALLED_APPS.append("jao_backend.oleeo.tests")

# Test embedding tag, not used in production.
TEST_TAG_ID = uuidv7(hex="0196a4fe-4e54-77de-9ff1-e13291404e5a")
TEST_TAG_MODEL = os.environ.get(
    "JAO_EMBEDDER_TEST_TAG", "sentence-transformers/all-MiniLM-L6-v2"
)

# During test + CI, embeddings should be avoided or small


EMBEDDING_TAGS = {
    **EMBEDDING_TAGS,
    TEST_TAG_ID: {
        # UUID is in UUID7 format, see
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

# Under test, Django will add "test" as a prefix to the database name and suffix a worker id under pytest-xdist
DEFAULT_TEST_DATABASE_NAME = "postgresql:///jao-backend"
# A Postgres database is used to simulate the oleeo database.
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
    # Keep the router configuration from common.py
    DATABASE_ROUTERS = ["jao_backend.common.routers.router.OleeoRouter"]
