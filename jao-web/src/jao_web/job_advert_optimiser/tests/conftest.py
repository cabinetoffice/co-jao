"""
Fixtures for job_advert_optimiser Django app of jao-web.
"""
import uuid

import pytest


@pytest.fixture
def session_key():
    return str(uuid.uuid4())


@pytest.fixture
def get_endpoint_for(settings):
    """
    Join the JAO_BACKEND_URL with 'applicants' ensuring exactly one slash between them.

    Args:
        settings: An object with JAO_BACKEND_URL attribute

    Returns:
        A properly joined URL string
    """

    base_url = settings.JAO_BACKEND_URL.rstrip('/')

    def get_endpoint(endpoint: str) -> str:
        return f"{base_url}/{endpoint}"

    return get_endpoint

@pytest.fixture
def similar_applicants_url(get_endpoint_for):
    return get_endpoint_for("similar-applicants")