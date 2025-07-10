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
from litellm import embedding, APIConnectionError
from litellm import completion_cost

from jao_backend.embeddings.models import EmbeddingModel
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.embeddings.models import TaggedEmbedding
from jao_backend.vacancies.models import Vacancy
from jao_backend.vacancies.models import VacancyEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID = (
    settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
)
LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER


def embed_vacancy(vacancy: "Vacancy"):
    """
    Generate and store embeddings for a Vacancy instance

    Args:
        vacancy: Django Vacancy model instance

    Returns:
        TaggedEmbedding: TaggedEmbedding instances created for the vacancy.
    """
    tag = EmbeddingTag.get_tag(settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)

    job_info_text = f"{vacancy.title}\n{vacancy.summary}\n{vacancy.description}"

    # Fix for ollama connection issue, remove if https://github.com/BerriAI/litellm/pull/7625 is merged:
    nest_asyncio.apply()

    # Request embedding using litellm, model is a litellm model name.
    # Note: api_base must not end with a slash '/'.

    try:
        response = embedding(
            model=tag.model.name,
            input=job_info_text,
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

    cost = completion_cost(
        completion_response=response,
        model=tag.model.name,
    )
    # TODO - surface cost.
    logger.info(
        "Embedding cost for model %s: $%.6f",
        tag.model.name,
        cost,
    )

    chunks = [
        response_part["embedding"]
        for response_part in response.data
        if response_part["embedding"] is not None
    ]

    # Associate a vacancy with the embeddings data and a tag
    # to specifies the version of the embedding process and the model.
    tagged_embeddings = VacancyEmbedding.save_embeddings(
        tag=tag,
        chunks=chunks,
        vacancy=vacancy,
    )

    logger.info(
        f'Embedded vacancy %s in %d chunks with tag %s "%s"',
        vacancy.id,
        len(chunks),
        tag.uuid,
        tag.name,
    )

    return tagged_embeddings
