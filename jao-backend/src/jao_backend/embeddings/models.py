from functools import lru_cache
from typing import List

import numpy as np
from django.db import models
from django.db import transaction
from django.utils.functional import classproperty
from pgvector.django import VectorField
from polymorphic.models import PolymorphicModel

from jao_backend.common.db.fields import UUIDField


class EmbeddingModel(models.Model):
    """Configurable vector types"""

    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)


class Embedding(PolymorphicModel):
    """
    General embedding model.
    Subclasses save the actual embedding field, so that different embedding sizes can be used.

    Includes:
    - History tracking via created_at


    NOTE:  In theory this class could be abstract, since the embedding field is
           provided by subclasses.

           To support FK relationships to this model abstract is False.
    """

    embedding_model = models.ForeignKey(
        EmbeddingModel, on_delete=models.PROTECT, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    @lru_cache(maxsize=None)
    def get_subclasses_by_dimensions(cls):
        return {
            subclass.embedding.field.dimensions: subclass
            for subclass in cls.__subclasses__()
        }

    @classmethod
    def get_subclass_for_embedding_dimensions(cls, dimensions: int):
        """
        Find the subclass of Embedding that matches the given dimensions.

        This is required to save embeddings, where an exact subclass is needed.

        >>> Embedding.get_subclass_for_embedding_size(768)
        <class 'jao_backend.ai.models.embedding.EmbeddingBase'>

        """
        return cls.get_subclasses_by_dimensions()[dimensions]

    @property
    def embedding(self):
        raise NotImplementedError("Subclasses implement the embedding property.")

    @classproperty
    def dimensions(self):
        """
        Get the dimensions of the embedding.
        """
        return self.embedding.field.dimensions

    def __str__(self):
        if type(self) is Embedding:
            return f"Embedding Base class instance, subclass to use"

        return f"{self.embedding} - {self.embedding_model.name}"


class EmbeddingTiny(Embedding):
    """
    384-dimensional embedding.

    This is fits all-minilm, which is mostly useful during local dev.
    """

    embedding = VectorField(dimensions=384, null=True)


class EmbeddingSmall(Embedding):
    """
    512-dimensional embedding (nomic-embed-text)
    Storage: ~3KB per vector
    """

    embedding = VectorField(dimensions=512, null=True)


class EmbeddingBase(Embedding):
    """
    768-dimensional embedding (nomic-embed-text)
    Storage: ~3KB per vector
    """

    embedding = VectorField(dimensions=768, null=True)


class EmbeddingLarge(Embedding):
    """
    1024-dimensional embedding, e.g.: mxbai-embed-large-v1
    Storage: ~4KB per vector
    """

    embedding = VectorField(dimensions=1024, null=True)


class EmbeddingXL(Embedding):
    """
    1536-dimensional embedding, e.g.: text-embedding-ada-002
    Storage: ~6KB per vector
    """

    embedding = VectorField(dimensions=1536, null=True)


class EmbeddingTag(models.Model):
    """
    Embedding tags allow us to specify embeddings by their purpose.
    If the text that goes into to the embedding tag is changed, then
    the version number should be incremented.

    A tag is associated with the process text goes through before embedding
    and how it's embedded.

    If any of these things change the version should be incremented,
    data using the older tag can either be kept or deleted at that point.

    A tag is unique across it's uuid and version.
    """

    uuid = UUIDField(db_index=True, version=7)
    name = models.CharField(max_length=50, unique=True)
    model = models.ForeignKey(
        EmbeddingModel,
        on_delete=models.PROTECT,
        db_index=True,
        help_text="The embedding model.",
    )
    model.__doc__ = "The embedding model may differ per config or instance."
    description = models.TextField()
    version = models.IntegerField(
        help_text="The version of the embedding tag.", default=0, blank=True, null=True
    )

    class Meta:
        verbose_name_plural = "Embedding Tags"
        constraints = [
            models.UniqueConstraint(
                fields=["uuid", "version"],
                name="unique_embedding_versioned_ag",
            ),
        ]

    def __str__(self):
        return self.name


class TaggedEmbedding(models.Model):
    """
    Tagged embeddings allow us to specify embeddings by their purpose,
    using tag names to differentiate them.
    """

    tag = models.ForeignKey(
        EmbeddingTag, on_delete=models.CASCADE, help_text="The tag of the embedding."
    )
    embedding = models.ForeignKey(
        Embedding, on_delete=models.CASCADE, help_text="The embedding."
    )
    chunk_index = models.IntegerField(
        help_text="The chunk ID of the embedding.", default=0, blank=True, null=True
    )

    class Meta:
        verbose_name_plural = "Tagged Embeddings"
        abstract = True

        constraints = [
            models.UniqueConstraint(
                fields=["tag", "embedding", "chunk_index", "version"],
                name="unique_vacancy_embedding_chunk",
            ),
        ]

    @classmethod
    def save_embeddings(cls, tag: EmbeddingTag, chunks: List[np.ndarray], **kwargs):
        """
        Save an embedding(s) for this vacancy, associated with an EmbeddingTag.

        If a subclass of TaggedEmbedding is used, it will be used to save the embedding,
        extra arguments can be passed to the save method using **kwargs.
        """
        with transaction.atomic():
            cls.objects.filter(tag__uuid=tag.uuid, tag__model=tag.model).delete()
            if not chunks:
                # No chunks to save, stick to the contract by returning an empty list.
                return []

            first_chunk = chunks[0]
            embedding_model = Embedding.get_subclass_for_embedding_dimensions(
                len(first_chunk)
            )

            return cls.objects.bulk_create(
                [
                    cls(
                        tag=tag,
                        embedding=embedding_model.objects.create(
                            embedding=chunk, embedding_model=tag.model
                        ),
                        chunk_index=i,
                        **kwargs,
                    )
                    for i, chunk in enumerate(chunks)
                ]
            )
