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

import litellm
import nest_asyncio
from django.conf import settings

from jao_backend.common.text_processing.clean_oleeo import strip_oleeo_bbcode
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

# Titan Text Embeddings V2 rejects input over 8192 tokens. We count with tiktoken (litellm's
# fallback for bedrock) which can disagree with Titan's own tokenizer, so keep real headroom.
MAX_EMBED_TOKENS = 7000


def _truncate_to_token_limit(text: str, model: str, max_tokens: int = MAX_EMBED_TOKENS) -> str:
    # ponytail: approximate tokenizer + margin, trims ~10% per pass. Good enough for
    # embeddings (leading text dominates); swap for the model's real tokenizer if drift matters.
    if litellm.token_counter(model=model, text=text) <= max_tokens:
        return text
    while text and litellm.token_counter(model=model, text=text) > max_tokens:
        text = text[: int(len(text) * 0.9)]
    return text


def embed_vacancy(vacancy: "Vacancy") -> "TaggedEmbedding":
    """
    Generate and store embeddings for a Vacancy instance

    Args:
        vacancy: Django Vacancy model instance

    Returns:
        TaggedEmbedding: TaggedEmbedding instances created for the vacancy.
    """
    tag = EmbeddingTag.get_tag(
        settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)

    # Data from OLEEO can contain bbcode, strip it before embedding.
    job_info_text = strip_oleeo_bbcode(
        f"{vacancy.title}\n{vacancy.person_spec}\n{vacancy.description}"
    )

    # Keep within the embedding model's input token limit (e.g. Titan V2 = 8192).
    job_info_text = _truncate_to_token_limit(job_info_text, tag.model.name)

    # Fix for ollama connection issue, remove if https://github.com/BerriAI/litellm/pull/7625 is merged:
    nest_asyncio.apply()

    response = tag.embed(job_info_text)
    cost = tag.completion_cost(response)  # noqa

    logger.info(
        "Embedding cost for model %s: $%.6f",
        tag.model.name,
        cost,
    )

    chunks = tag.response_chunks(response)

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
