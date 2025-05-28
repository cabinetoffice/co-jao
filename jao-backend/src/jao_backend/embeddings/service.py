"""
Embedding generation service which supports both AWS Bedrock Titan embeddings and
existing local sentence-transformer models

Works with or without Django settings

Adds:
- Configurable embedding backends
- Automatic fallback mechanisms
- Hybrid deployment options
"""

import logging
from functools import lru_cache

import nest_asyncio
from django.conf import settings
from litellm import embedding

from jao_backend.embeddings.models import EmbeddingTag, EmbeddingModel
from jao_backend.embeddings.models import TaggedEmbedding
from jao_backend.vacancies.models import Vacancy, VacancyEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID = settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER

class EmbeddingService:

    @classmethod
    @lru_cache(maxsize=None)
    def sync_embedding_tags(cls):
        """
        Synchronize embedding tags with the database.

        This is behind lru_cache as it should only be called once per process.
        """
        for tag_data in settings.EMBEDDING_TAGS.values():
            model_name = tag_data.pop('model')
            model, _ = EmbeddingModel.objects.get_or_create(name=model_name, defaults={"is_active": True})

            tag_data['model'] = model
            tag, _ = EmbeddingTag.objects.get_or_create(
                defaults=tag_data, uuid=tag_data['uuid'], version=tag_data['version']
            )

    @classmethod
    def create_for_vacancy(cls, vacancy: "Vacancy"):
        """
        Generate and store embeddings for a Vacancy instance

        Args:
            vacancy: Django Vacancy model instance

        Returns:
            TaggedEmbedding: TaggedEmbedding instances created for the vacancy.
        """
        cls.sync_embedding_tags()

        # Tags store a unique id and name for the embedding process, as well as the model name
        tag_data = settings.EMBEDDING_TAGS[settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID]

        tag, _ = EmbeddingTag.objects.get_or_create(
            defaults=tag_data, uuid=settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
        )

        job_info_text = f"{vacancy.job_title}\n{vacancy.responsibilities}"

        # Fix for ollama connection issue, remove if https://github.com/BerriAI/litellm/pull/7625 is merged:
        nest_asyncio.apply()

        # Request embedding using litellm, model is a litellm model name.
        # Note: api_base must not end with a slash '/'.
        response = embedding(
            model=tag.model.name,
            input=job_info_text,
            api_base=LITELLM_API_BASE,
            custom_llm_provider=LITELLM_CUSTOM_PROVIDER,
        )

        chunks = [
            response_part['embedding'] for response_part in response.data
            if response_part['embedding'] is not None
        ]

        # Associate a vacancy with the embeddings data and a tag
        # to specifies the version of the embedding process and the model.
        tagged_embeddings = VacancyEmbedding.save_embeddings(
            tag=tag,
            chunks=chunks,
            vacancy=vacancy,
        )
        logger.info(f"Generated embeddings for vacancy {vacancy.id} with tag {tag.uuid}")

        return tagged_embeddings
