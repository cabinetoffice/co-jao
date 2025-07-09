import pytest
from pytest_unordered import unordered

from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.embeddings.service import EmbeddingService


@pytest.mark.django_db
def test_sync_embedding_tags(settings):
    """
    Verify that calling sync_embedding_tags creates
    the expected embedding tags in the database.
    """
    expected_tags = [
        {
            "uuid": settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID,
            "name": "job-title-responsibilities",
            "model__name": "sentence-transformers/all-MiniLM-L6-v2",
            "description": "Description for Vacancy Tag 1",
            "version": 1,
        },
        {
            "uuid": settings.TEST_TAG_ID,
            "name": "test-tag",
            "model__name": "sentence-transformers/all-MiniLM-L6-v2",
            "description": "Description for Test Tag",
            "version": 1,
        },
    ]

    # On a fresh database there should be no embedding tags yet
    assert EmbeddingTag.objects.exists() is False

    EmbeddingService.sync_embedding_tags()

    actual_tags = [
        *EmbeddingTag.objects.values(
            "uuid", "name", "model__name", "description", "version"
        )
    ]

    assert actual_tags == unordered(expected_tags)
