import numpy as np
import pytest

from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.embeddings.models import EmbeddingTiny
from jao_backend.embeddings.service import EmbeddingService
from jao_backend.vacancies.models import VacancyEmbedding

from .factories import VacancyFactory


@pytest.mark.django_db
def test_vacancy_embedding_save_embeddings():
    """
    VacancyEmbedding.save_embeddings should save VacancyEmbedding instances,
    that link Vacancy and EmbeddingTag instances.
    """
    EmbeddingService.sync_embedding_tags.cache_clear()
    EmbeddingService.sync_embedding_tags()

    tag = EmbeddingTag.objects.order_by("-version").get(
        name="job-title-responsibilities"
    )
    vacancy = VacancyFactory.create()
    assert vacancy.vacancyembedding_set.exists() is False

    # Use random floats to stand in for the embedding
    fake_embeddings = [np.random.rand(EmbeddingTiny.dimensions)]

    saved_embeddings = VacancyEmbedding.save_embeddings(
        tag=tag, chunks=fake_embeddings, vacancy=vacancy
    )

    assert (
        0 < len(saved_embeddings) == len(fake_embeddings)
    ), "Failed to save embeddings"
    assert list(vacancy.vacancyembedding_set.all()) == saved_embeddings
