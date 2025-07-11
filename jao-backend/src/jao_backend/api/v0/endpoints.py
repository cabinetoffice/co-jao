import logging

from django.conf import settings
from django.http import HttpRequest

import numpy as np
from ninja import NinjaAPI

from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.maps import AreaFrequenciesResponse
from jao_backend_schemas.plots import PlotlyFiguresResponse
from jao_backend_schemas.vacancies import SimilarVacanciesResponse
from jao_backend_schemas.vacancies import JobDescriptionRequest
from jao_backend_schemas.vacancies import VacancyListing

from jao_backend.common.text_processing.clean_bbcode import strip_bbcode
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import VacancyEmbedding

logger = logging.getLogger(__name__)

api = NinjaAPI(
    version="0.1.0",
    title="Legacy Jao Backend API",
    description="Legacy API for Jao Backend",
)


def get_similar_vacancies(text, top_n=10):
    tag = EmbeddingTag.get_tag(settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)
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

    return [
        vacancy_embedding.vacancy for vacancy_embedding in similar_vacancy_embeddings
    ]


@api.post("/advice")
def advice(request: HttpRequest, payload: JobDescriptionRequest) -> AdviceResponse:
    logger.info(
        "STUB: advice endpoint called with description: %s", payload.description
    )
    text = """
    This is a sample advice to help improve your job description."""
    logger.info("STUB: advice sending example advice: %s", text)
    return AdviceResponse(advice=text)


@api.post("/similar_adverts", response=SimilarVacanciesResponse)
def similar_adverts(
    request: HttpRequest, payload: JobDescriptionRequest
) -> SimilarVacanciesResponse:
    # For now convert this into the older format
    similar_vacancies_list = [
        VacancyListing.model_validate(
            {
                "job_title": vacancy.title,
                "full_job_desc": strip_bbcode(vacancy.description),
                "vacancy_id": vacancy.pk,
            }
        )
        for vacancy in get_similar_vacancies(payload.description, top_n=10)
    ]
    return SimilarVacanciesResponse(similar_vacancies=similar_vacancies_list)


@api.post("/similar_advert_plots")
def similar_advert_plots(
    request: HttpRequest, payload: JobDescriptionRequest
) -> PlotlyFiguresResponse:
    """
    Get a graph of the job description.
    """
    # Stub: this required aggregated data
    logger.info(
        "STUB: similar_advert_plots endpoint called with description: %s",
        payload.description,
    )
    graphs = []
    return PlotlyFiguresResponse(plotly_figures=graphs)


@api.post("/skills_plots")
def skills_plots(request, payload: JobDescriptionRequest) -> PlotlyFiguresResponse:
    """
    Get a graph of the job description.
    """
    # Stub: skills are not ingested right now.
    logger.info(
        "STUB: skills_plots endpoint called with description: %s", payload.description
    )
    graphs = []
    result = PlotlyFiguresResponse(plotly_figures=graphs)
    return result


@api.post("/applicant_locations")
def applicant_locations(
    request, payload: JobDescriptionRequest
) -> AreaFrequenciesResponse:
    # Stub: OLEEO ingestion of locations is TBD
    logger.info(
        "STUB: applicant_locations endpoint called with description: %s",
        payload.description,
    )
    return AreaFrequenciesResponse(area_frequencies=[])
