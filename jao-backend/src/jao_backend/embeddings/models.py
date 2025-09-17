import logging

from cachemethod import lru_cachemethod
from functools import cache
from typing import List

import numpy as np

from django.conf import settings
from django.db import models
from django.db import transaction
from django.utils.functional import classproperty
from pgvector.django import VectorField
from polymorphic.models import PolymorphicModel

from litellm import APIConnectionError, completion_cost
from litellm import embedding

from jao_backend.common.db.fields import UUIDField
from jao_backend.embeddings.querysets import EmbeddingTagQuerySet

logger = logging.getLogger(__name__)

LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER


class EmbeddingModel(models.Model):
    """Configurable vector types"""

    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


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
    """This is the output of `litellm.completion_cost` for the embedding model used."""

    @classmethod
    @cache
    def get_subclasses_by_dimensions(cls):
        """
        Note: not recursive, though hasn't been needed yet.
        """
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
        raise NotImplementedError(
            "Subclasses implement the embedding property.")

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

    objects = EmbeddingTagQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Embedding Tags"
        constraints = [
            models.UniqueConstraint(
                fields=["uuid", "version"],
                name="unique_embedding_versioned_ag",
            ),
        ]

    @lru_cachemethod(maxsize=1)
    def embed(self, text: str):
        """
        Call LITELLM to embed the text using this tag's model.

        :return: litellm.EmbeddingResponse, see litellm.embedding
                https://deepwiki.com/mikeplavsky/litellm/2.1-completion-and-embedding-functions#example-usage---embedding
        """
        # Request embedding using litellm, model is a litellm model name.
        # Note: api_base must not end with a slash '/'.

        try:
            response = embedding(
                model=self.model.name,
                input=text,
                api_base=LITELLM_API_BASE,
                custom_llm_provider=LITELLM_CUSTOM_PROVIDER,
            )
        except APIConnectionError as e:
            logger.error(
                "Connection refused to the embedding service. "
                "Ensure the service is running and accessible: %s",
                e,
            )
            raise

        return response

    @staticmethod
    def completion_cost(response, **kwargs):
        """
        Call with the output of .embed to get an estimate of the cost,
        see litellm.completion_cost.
        """
        cost = completion_cost(
            completion_response=response,
            model=kwargs.get("model") or response.model,
        )
        return cost

    @staticmethod
    def response_chunks(response):
        """
        Get the chunks of the embedding response.

        These chunks can be passed save_embeddings as implemented by
        subclasses of `Embedding`, to link embeddings to a specific
        record in a table.
        """
        return [
            response_part["embedding"]
            for response_part in response.data
            if response_part["embedding"] is not None
        ]

    @classmethod
    @cache
    def get_configured_tags(cls):
        """
        :return: dict[str, EmbeddingTag]

        Also, synchronizes the tags in the database with the tags configured in settings.

        Tags are setup in settings, this allows us to have different models on AWS vs local,
        for the different named tags specified there.
        """
        tags = {}
        for tag_data in settings.EMBEDDING_TAGS.values():
            model_name = tag_data.pop("model")
            model, _ = EmbeddingModel.objects.get_or_create(
                name=model_name, defaults={"is_active": True}
            )

            tag_data["model"] = model
            # update_or_create is be used here to pick up changes from the settings.
            tag, _ = cls.objects.update_or_create(
                uuid=tag_data["uuid"], version=tag_data["version"], defaults=tag_data
            )

            tags[tag.uuid] = tag

        return tags

    @classmethod
    def get_tag(cls, uuid: str):
        """
        Get a tag by its UUID.

        This is used to get the tag for a specific embedding.

        Calls `get_configured_tags` which syncs tags from settings.
        """
        tags = EmbeddingTag.get_configured_tags()
        return tags.get(uuid)

    def __str__(self):
        return f"{self.name} (v{self.version}) model={self.model.name}"


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

        kwargs should be used to filter to a specific model of cls, this is used to
        clear previous embeddings.
        """
        assert kwargs, "kwargs must be provided to filter the model of cls."

        with transaction.atomic():
            cls.objects.filter(
                tag__uuid=tag.uuid, tag__model=tag.model, **kwargs
            ).delete()
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
