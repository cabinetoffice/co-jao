import pytest
from django.utils import timezone

from jao_backend.oleeo.tests.factories import InvalidTestVacanciesFactory
from jao_backend.oleeo.tests.factories import TestListAgeGroupFactory
from jao_backend.oleeo.tests.factories import TestVacanciesFactory


@pytest.fixture
def enable_oleeo_db(settings):
    settings.JAO_ENABLE_OLEEO_DB = True


@pytest.fixture(scope="session")
def age_group_list_data() -> list[str]:
    """
    Tuples of (id, description) for age groups.
    """
    return [
        "Prefer not disclose",
        "16-24",
        "25-29",
        "30-34",
        "35-39",
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
        "65+",
    ]


@pytest.mark.django_db
@pytest.fixture
def age_group_instances(age_group_list_data: list[str], enable_oleeo_db):
    """
    Converts the age group data into a list of dictionaries.
    """
    return [
        TestListAgeGroupFactory.create(
            age_group_id=age_group_id,
            age_group_desc=age_group_desc,
            row_last_updated=timezone.now(),
        )
        for (age_group_id, age_group_desc) in enumerate(age_group_list_data, 1)
    ]


@pytest.fixture
def valid_test_vacancy_data():
    """Test data for vacancies with valid salary fields."""
    return [
        {
            "vacancy_id": 1,
            "vacancy_title": "Valid Vacancy 1",
            "salary_minimum": "50000",
            "salary_maximum_optional": "60000",
            "live_date": "2023-01-01T00:00:00Z",
            "closing_date": "2023-01-31T00:00:00Z",
        },
        {
            "vacancy_id": 2,
            "vacancy_title": "Valid Vacancy 2 - No Max",
            "salary_minimum": "45000",
            "salary_maximum_optional": None,
            "live_date": "2023-02-01T00:00:00Z",
            "closing_date": "2023-02-28T00:00:00Z",
        },
        {
            "vacancy_id": 3,
            "vacancy_title": "Valid Vacancy 3 - Empty Max",
            "salary_minimum": "40000",
            "salary_maximum_optional": "",
        },
    ]


@pytest.fixture
def invalid_test_vacancy_data():
    """Test data for vacancies with invalid salary fields."""
    return [
        {
            "vacancy_id": 10,
            "vacancy_title": "Invalid - Null Salary Min",
            "salary_minimum": None,
            "salary_maximum_optional": "55000",
        },
        {
            "vacancy_id": 11,
            "vacancy_title": "Invalid - Comma in Salary",
            "salary_minimum": "50,000",
            "salary_maximum_optional": "60,000",
        },
        {
            "vacancy_id": 12,
            "vacancy_title": "Invalid - Text Salary",
            "salary_minimum": "fifty thousand",
            "salary_maximum_optional": "sixty thousand",
        },
        {
            "vacancy_id": 13,
            "vacancy_title": "Invalid - Very Large Number",
            "salary_minimum": "999999999999999999999",
            "salary_maximum_optional": "50000",
        },
    ]


@pytest.fixture
def valid_test_vacancy_instances():
    """Create test vacancy instances with valid salary data."""
    return TestVacanciesFactory.create_batch(3)


@pytest.fixture
def invalid_test_vacancy_instances():
    """Create test vacancy instances with invalid salary data."""
    return [
        InvalidTestVacanciesFactory(invalid_type=True),
        InvalidTestVacanciesFactory(comma_in_salary=True),
        InvalidTestVacanciesFactory(text_salary=True),
        InvalidTestVacanciesFactory(very_large_number=True),
    ]
