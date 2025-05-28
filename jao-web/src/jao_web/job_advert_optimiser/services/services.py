"""
Access the JAO backend services.
"""

import logging

import httpx
from django.conf import settings

from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.maps import AreaFrequenciesResponse
from jao_backend_schemas.plots import PlotlyFiguresResponse
from jao_backend_schemas.vacancies import JobDescriptionRequest, SimilarVacanciesResponse
from jao_web.job_advert_optimiser.services.problem_details import raise_exception_on_problem

logger = logging.getLogger(__name__)

JAO_BACKEND_URL = settings.JAO_BACKEND_URL
JAO_SERVICE_TIMEOUT = settings.JAO_BACKEND_TIMEOUT


async def get_advice(client: httpx.AsyncClient, description: str) -> AdviceResponse:
    request = JobDescriptionRequest(description=description)
    response = await client.post(
        "advisor/advice", json=request.model_dump(), timeout=JAO_SERVICE_TIMEOUT
    )
    raise_exception_on_problem(response)
    return AdviceResponse.model_validate(response.json())


async def get_similar_adverts(
    client: httpx.AsyncClient, description: str
) -> SimilarVacanciesResponse:
    """
    Similar vacancies.
    """
    request = JobDescriptionRequest(description=description)
    response = await client.post(
        "similar_adverts", json=request.model_dump(), timeout=JAO_SERVICE_TIMEOUT
    )
    raise_exception_on_problem(response)
    return SimilarVacanciesResponse.model_validate(response.json(), strict=True)


async def get_demographics_plots(
    client: httpx.AsyncClient, description: str
) -> PlotlyFiguresResponse:
    """
    Demographics plots for similar vacancies.
    """
    request = JobDescriptionRequest(description=description)
    response = await client.post(
        "similar_advert_plots", json=request.model_dump(), timeout=JAO_SERVICE_TIMEOUT
    )
    raise_exception_on_problem(response)
    return PlotlyFiguresResponse.model_validate(response.json(), strict=True)


async def get_skills_plots(
    client: httpx.AsyncClient, description: str
) -> PlotlyFiguresResponse:
    """
    Skills plots for similar vacancies.
    """
    request = JobDescriptionRequest(description=description)
    response = await client.post(
        "skills_plots", json=request.model_dump(), timeout=JAO_SERVICE_TIMEOUT
    )
    raise_exception_on_problem(response)
    return PlotlyFiguresResponse.model_validate(response.json(), strict=True)


async def get_applicant_locations(
    client: httpx.AsyncClient, description: str
) -> AreaFrequenciesResponse:
    request = JobDescriptionRequest(description=description)
    response = await client.post(
        "applicant_locations", json=request.model_dump(), timeout=JAO_SERVICE_TIMEOUT
    )

    raise_exception_on_problem(response)
    return AreaFrequenciesResponse.model_validate(response.json(), strict=True)
