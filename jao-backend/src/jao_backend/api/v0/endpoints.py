import hashlib
from django.core.cache import cache
import logging
import json
from django.conf import settings
from django.http import HttpRequest, StreamingHttpResponse

import numpy as np
from ninja import NinjaAPI

from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.advice import AdviceRequest
from jao_backend_schemas.draft import DraftResponse
from jao_backend_schemas.draft import DraftRequest
from jao_backend_schemas.maps import AreaFrequenciesResponse
from jao_backend_schemas.plots import PlotlyFiguresResponse
from jao_backend_schemas.vacancies import SimilarVacanciesResponse
from jao_backend_schemas.vacancies import JobDescriptionRequest
from jao_backend_schemas.vacancies import VacancyListing

from jao_backend.common.text_processing.clean_oleeo import parse_oleeo_bbcode
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import VacancyEmbedding
from jao_backend.llm.llm_service import LLMService
llm_service = LLMService()

logger = logging.getLogger(__name__)

api = NinjaAPI(
    version="0.1.0",
    title="Legacy Jao Backend API",
    description="Legacy API for Jao Backend",
)

'''
    Turn these into 1 endpoint which uses a Django channel websocket to send
    back each current POSTs
'''


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


@api.post("/similar_adverts", response=SimilarVacanciesResponse)
def similar_adverts(
    request: HttpRequest, payload: JobDescriptionRequest
) -> SimilarVacanciesResponse:
    similar_vacancies_list = [
        VacancyListing.model_validate(
            {
                "job_title": vacancy.title,
                "full_job_desc": parse_oleeo_bbcode(vacancy.description),
                "vacancy_id": vacancy.pk,
            }
        )
        for vacancy in get_similar_vacancies_cached(payload.description, top_n=10)
    ]
    return SimilarVacanciesResponse(similar_vacancies=similar_vacancies_list)


@api.post("/advice")
def advice(request: HttpRequest, payload: AdviceRequest) -> StreamingHttpResponse:
    formatted_vacancies = [
        f"Job Title: {vacancy.job_title}\nDescription: {
            parse_oleeo_bbcode(vacancy.full_job_desc)}"
        for vacancy in payload.similar_vacancies
    ]

    def generate():
        """Generator for streaming response"""
        for chunk in llm_service.get_advice(payload.description,
                                            formatted_vacancies,
                                            payload.advice_type):
            logger.debug(f"Streaming chunk: {chunk}")
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        yield "data: [DONE]\n\n"
    return StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )


@api.post("/draft")
def draft(request: HttpRequest, payload: DraftResponse) -> StreamingHttpResponse:
    formatted_vacancies = [
        f"Job Title: {vacancy.job_title}\nDescription: {
            parse_oleeo_bbcode(vacancy.full_job_desc)}"
        for vacancy in payload.similar_vacancies
    ]

    def generate():
        for chunk in llm_service.get_draft(payload.description, formatted_vacancies):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"
    return StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )


# Write a query using the similar vacancies data from application stastics -
# aggregated application statistic model


# @api.post("/similar_advert_plots")
# def similar_advert_plots(
#     request: HttpRequest, payload: JobDescriptionRequest
# ) -> PlotlyFiguresResponse:
#     """
#     Get a graph of the job description.
#     """
#     # Stub: this required aggregated data
#     logger.info(
#         "STUB: similar_advert_plots endpoint called with description: %s",
#         payload.description,
#     )
#     graphs = []
#     return PlotlyFiguresResponse(plotly_figures=graphs)
#
# # ADD Skills Ingester to write skills to DB
#
#
# @api.post("/skills_plots")
# def skills_plots(request, payload: JobDescriptionRequest) -> PlotlyFiguresResponse:
#     """
#     Get a graph of the job description.
#     """
#     # Stub: skills are not ingested right now.
#     logger.info(
#         "STUB: skills_plots endpoint called with description: %s", payload.description
#     )
#     graphs = []
#     result = PlotlyFiguresResponse(plotly_figures=graphs)
#     return result
#
# # Maybe REMOVE the location response
#
#
# @api.post("/applicant_locations")
# def applicant_locations(
#     request, payload: JobDescriptionRequest
# ) -> AreaFrequenciesResponse:
#     # Stub: OLEEO ingestion of locations is TBD
#     logger.info(
#         "STUB: applicant_locations endpoint called with description: %s",
#         payload.description,
#     )
#     area_frequencies: AreaFrequencyProperties = []
#     # TODO: populate area_frequencies with instances of AreaFrequencyProperties from the database.
#     return AreaFrequenciesResponse(area_frequencies=area_frequencies)
