import pytest

from jao_backend.embeddings.models import Embedding
from jao_backend.embeddings.models import EmbeddingBase
from jao_backend.embeddings.models import EmbeddingLarge
from jao_backend.embeddings.models import EmbeddingSmall
from jao_backend.embeddings.models import EmbeddingTiny
from jao_backend.embeddings.models import EmbeddingXL


@pytest.mark.parametrize(
    "dimensions, embedding_subclass",
    [
        (384, EmbeddingTiny),
        (512, EmbeddingSmall),
        (768, EmbeddingBase),
        (1024, EmbeddingLarge),
        (1536, EmbeddingXL),
    ],
)
@pytest.mark.django_db
def test_get_embedding_subclass_by_dimension(dimensions, embedding_subclass):
    """
    Passing in a dimension with a subclass should return that it.
    """
    actual_subclass = Embedding.get_subclass_for_embedding_dimensions(dimensions)

    assert actual_subclass is embedding_subclass
    assert actual_subclass.embedding.field.dimensions == dimensions


def test_get_embedding_subclass_by_invalid_dimension():
    """
    Attempting to get a subclass for an invalid dimension should raise a KeyError.
    """
    with pytest.raises(KeyError):
        Embedding.get_subclass_for_embedding_dimensions(9999)
