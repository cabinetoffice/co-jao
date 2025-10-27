import numpy as np
import hashlib
from django.core.cache import cache
from jao_backend_schemas.vacancies import VacancyListing

from jao_backend.common.text_processing.clean_oleeo import parse_oleeo_bbcode
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import VacancyEmbedding

from django.conf import settings


def get_similar_vacancies_cached(text, top_n=10):
    """Cached version of get_similar_vacancies"""
    cache_key = f"similar_vacancies_{
        hashlib.md5(text.encode()).hexdigest()}_{top_n}"

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = get_similar_vacancies(text, top_n)
    cache.set(cache_key, result, timeout=300)
    return result


def get_similar_vacancies(text, top_n=10):
    tag = EmbeddingTag.get_tag(
        settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)
    response = tag.embed(text)
    chunks = tag.response_chunks(response)

    if len(chunks) > 1:
        # TODO: revisit this when we have chunks representing different parts of the text
        query_vector = np.mean(chunks, axis=0)
    else:
        query_vector = chunks[0]  # for now take the first chunk

    similar_vacancy_embeddings = (
        VacancyEmbedding.objects.filter(tag=tag)
        .distance(query_vector)
        .select_related("vacancy", "embedding")
        .order_by("distance")[:top_n]
    )

    tag = EmbeddingTag.get_tag(
        settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)
    similar_vacancy_embeddings = VacancyEmbedding.objects.similar_vacancies(
        text, tag, top_n)
    return [
        vacancy_embedding.vacancy for vacancy_embedding in similar_vacancy_embeddings
    ]
