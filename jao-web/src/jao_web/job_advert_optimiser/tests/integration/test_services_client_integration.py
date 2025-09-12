import pytest

from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.maps import AreaFrequenciesResponse
from jao_web.job_advert_optimiser.services.client import get_async_client
from jao_web.job_advert_optimiser.services.services import (
    get_advice,
    get_similar_adverts,
    get_demographics_plots,
    get_skills_plots,
    get_applicant_locations,
)

# Common test data
SAMPLE_JOB_DESCRIPTION = """
Software Engineer - Python Developer
We are seeking a skilled Python developer to join our team. The ideal candidate will have:
- 3+ years experience with Python
- Experience with Django and FastAPI
- Strong understanding of REST APIs
- Knowledge of SQL and database design
Location: London
Salary: £50,000 - £70,000
"""


@pytest.fixture
def service_client(session_key):
    """Fixture to provide an async client for all tests."""
    return get_async_client(session_key)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_advice_integration(service_client):
    """Test the get_advice endpoint with real backend."""
    advice_response = await get_advice(service_client, SAMPLE_JOB_DESCRIPTION)
    assert isinstance(advice_response, AdviceResponse)
    assert advice_response.advice, "Advice list should not be empty"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_similar_adverts_integration(service_client):
    """Test the get_similar_adverts endpoint with real backend."""
    from jao_backend_schemas.vacancies import SimilarVacanciesResponse

    similar_adverts = await get_similar_adverts(service_client, SAMPLE_JOB_DESCRIPTION)
    assert isinstance(similar_adverts, SimilarVacanciesResponse)
    assert similar_adverts.similar_vacancies, "Similar vacancies list should not be empty"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_demographics_plots_integration(service_client):
    """Test the get_demographics_plots endpoint with real backend."""
    from jao_backend_schemas.plots import PlotlyFiguresResponse

    demographics = await get_demographics_plots(service_client, SAMPLE_JOB_DESCRIPTION)
    figures = demographics.get_figures()

    assert isinstance(demographics, PlotlyFiguresResponse)
    assert figures, "Figures list should not be empty"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_skills_plots_integration(service_client):
    """Test the get_skills_plots endpoint with real backend."""
    from jao_backend_schemas.plots import PlotlyFiguresResponse

    skills = await get_skills_plots(service_client, SAMPLE_JOB_DESCRIPTION)
    figures = skills.get_figures()

    assert isinstance(skills, PlotlyFiguresResponse)
    assert figures, "Figures list should not be empty"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_applicant_locations_integration(service_client):
    """Test the get_applicant_locations endpoint with real backend."""
    locations = await get_applicant_locations(service_client, SAMPLE_JOB_DESCRIPTION)
    assert isinstance(locations, AreaFrequenciesResponse)
    assert locations.area_frequencies, "Area frequencies list should not be empty"
