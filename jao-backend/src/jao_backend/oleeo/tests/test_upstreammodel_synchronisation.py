from datetime import timedelta

import pytest
from django.db.models import QuerySet

from jao_backend.application_statistics.models import AgeGroup
from jao_backend.oleeo.base_querysets import UpstreamModelQuerySet
from jao_backend.oleeo.tests.fixtures import age_group_instances
from jao_backend.oleeo.tests.fixtures import age_group_list_data
from jao_backend.oleeo.tests.fixtures import enable_oleeo_db
from jao_backend.oleeo.tests.fixtures import invalid_test_vacancy_data
from jao_backend.oleeo.tests.fixtures import invalid_test_vacancy_instances
from jao_backend.oleeo.tests.fixtures import valid_test_vacancy_data
from jao_backend.oleeo.tests.fixtures import valid_test_vacancy_instances
from jao_backend.oleeo.tests.models import TestListAgeGroup
from jao_backend.oleeo.tests.models import TestVacancies


@pytest.mark.django_db
def test_as_destination_values_outputs_expected_values(age_group_instances):
    """
    Verify that as_destination_values() correctly maps source fields to destination fields.
    """
    # Assumption check; otherwise the rest of the test won't be valid
    assert TestListAgeGroup.destination_model == "application_statistics.AgeGroup"

    # Set a new description so we can verify it gets set in the destination model
    new_description = "Renamed age group"

    source_instance = age_group_instances[0]
    source_instance.age_group_desc = new_description
    source_instance.save()

    destination_values = [
        *TestListAgeGroup.objects_for_ingest.filter(pk=source_instance.pk).as_destination_values()
    ]

    assert len(destination_values) == 1
    destination_value = destination_values[0]

    assert destination_value["id"] == source_instance.pk
    assert destination_value["description"] == new_description
    assert destination_value["last_updated"] == source_instance.row_last_updated


@pytest.mark.django_db
@pytest.mark.parametrize(
    "include_keys",
    [
        {"description"},
        {"description", "last_updated"},
    ],
)
def test_as_destination_values_include_parameter(age_group_instances, include_keys):
    """
    Verify that as_destination_values() respects the include parameter.
    """
    source_instance = age_group_instances[0]
    values_list = list(
        TestListAgeGroup.objects_for_ingest.filter(pk=source_instance.pk).as_destination_values(
            *include_keys
        )
    )

    assert len(values_list) == 1
    values = values_list[0]

    assert set(values.keys()) == include_keys


def test_get_destination_model():
    """
    Verify that get_destination_model() returns the correct destination model.
    """
    assert TestListAgeGroup.destination_model == "application_statistics.AgeGroup"
    assert TestListAgeGroup.get_destination_model() == AgeGroup


@pytest.mark.django_db
def test_as_destination_instances_creates_model_instances(age_group_instances):
    """
    Verify that as_destination_instances() creates destination model instances with correct data.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    source_instance = age_group_instances[0]
    destination_instances = [
        *TestListAgeGroup.objects_for_ingest.filter(
            pk=source_instance.pk
        ).as_destination_instances()
    ]
    assert len(destination_instances) == 1

    destination_instance = destination_instances[0]

    assert isinstance(destination_instance, AgeGroup)
    assert destination_instance.id == source_instance.pk
    assert destination_instance.description == source_instance.age_group_desc
    assert destination_instance.last_updated == source_instance.row_last_updated


@pytest.mark.django_db
def test_as_destination_instances_not_backed_by_database(age_group_instances):
    """
    Verify that as_destination_instances() creates instances, these instances are not backed
    by the database yet - so don't have pks set.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    source_instance = age_group_instances[0]
    destination_instance = [
        *TestListAgeGroup.objects_for_ingest.filter(
            pk=source_instance.pk
        ).as_destination_instances()
    ]

    assert len(destination_instance) == 1
    destination_instance = destination_instance[0]

    assert isinstance(destination_instance, AgeGroup)
    assert destination_instance.id == source_instance.pk
    assert not AgeGroup.objects.filter(pk=source_instance.pk).exists()


@pytest.mark.django_db
def test_as_destination_instances_with_multiple_records(age_group_instances):
    """
    Verify that as_destination_instances() works with multiple source records.
    """
    assert len(age_group_instances) >= 2, "Need at least 2 instances for this test"

    expected_pks = [age_group_instances[0].pk, age_group_instances[1].pk]
    source_descriptions = [
        *TestListAgeGroup.objects_for_ingest.filter(pk__in=expected_pks).values_list(
            "age_group_desc", flat=True
        )
    ]

    destination_instances = [
        *TestListAgeGroup.objects_for_ingest.filter(pk__in=expected_pks).as_destination_instances()
    ]

    AgeGroup.objects.bulk_create(destination_instances)

    actual_pks = [
        *AgeGroup.objects.filter(description__in=source_descriptions).values_list(
            "pk", flat=True
        )
    ]

    assert set(actual_pks) == set(expected_pks)


@pytest.mark.django_db
def test_as_destination_instances_empty_queryset(age_group_instances):
    """
    Verify that as_destination_instances() handles empty querysets correctly.
    """
    destination_instances = [
        *TestListAgeGroup.objects_for_ingest.none().as_destination_instances()
    ]

    assert destination_instances == []


@pytest.mark.django_db
def test_as_destination_instances_intended_for_bulk_create(age_group_instances):
    """
    Verify that as_destination_instances() produces instances suitable for bulk_create().
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    expected_pks = {instance.pk for instance in age_group_instances}

    destination_instances = [*TestListAgeGroup.objects_for_ingest.as_destination_instances()]
    AgeGroup.objects.bulk_create(destination_instances)

    actual_pks = set(AgeGroup.objects.values_list("pk", flat=True))

    assert actual_pks == expected_pks


@pytest.mark.django_db
def test_as_destination_values_list_basic(age_group_instances):
    """
    Verify that as_destination_values_list() returns tuples of destination values.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    source_instance = age_group_instances[0]
    values_list = [
        *TestListAgeGroup.objects_for_ingest.filter(
            pk=source_instance.pk
        ).as_destination_values_list("id", "description")
    ]

    assert values_list == [(source_instance.pk, source_instance.age_group_desc)]


@pytest.mark.django_db
def test_as_destination_values_list_flat(age_group_instances):
    """
    Verify that as_destination_values_list() with flat=True returns single values.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    source_instance = age_group_instances[0]
    flat_values_list = [
        *TestListAgeGroup.objects_for_ingest.filter(
            pk=source_instance.pk
        ).as_destination_values_list("description", flat=True)
    ]

    assert flat_values_list == [source_instance.age_group_desc]


@pytest.mark.django_db
def test_valid_for_ingest_base_implementation(age_group_instances):
    """
    Verify that `valid_for_ingest` base implementation returns the same queryset.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    original_qs = TestListAgeGroup.objects_for_ingest.all()
    filtered_qs = original_qs.valid_for_ingest()

    original_pks = set(original_qs.values_list("pk", flat=True))
    filtered_pks = set(filtered_qs.values_list("pk", flat=True))

    assert original_pks == filtered_pks


@pytest.mark.django_db
def test_vacancies_valid_for_ingest_filters_invalid_data(
    valid_test_vacancy_instances, invalid_test_vacancy_instances
):
    """
    Verify that `VacanciesQuerySet.valid_for_ingest()` filters out records with invalid salary data.
    """
    total_count = len(valid_test_vacancy_instances) + len(
        invalid_test_vacancy_instances
    )
    assert (
        TestVacancies.objects_for_ingest.count() == total_count
    ), "Sanity check: all test vacancies created"

    valid_pks = set(
        TestVacancies.objects_for_ingest.valid_for_ingest().values_list("pk", flat=True)
    )
    expected_valid_pks = {
        instance.vacancy_id for instance in valid_test_vacancy_instances
    }

    assert valid_pks == expected_valid_pks


@pytest.mark.django_db
def test_vacancies_valid_for_ingest_with_only_valid_data(valid_test_vacancy_instances):
    """
    Verify that `valid_for_ingest` returns all records when all data is valid.
    """
    assert (
        len(valid_test_vacancy_instances) > 0
    ), "Sanity check: should have valid test vacancies"

    all_vacancies_pks = set(TestVacancies.objects_for_ingest.values_list("vacancy_id", flat=True))
    valid_vacancies_pks = set(
        TestVacancies.objects_for_ingest.valid_for_ingest().values_list("vacancy_id", flat=True)
    )

    assert all_vacancies_pks == valid_vacancies_pks


@pytest.mark.django_db
def test_vacancies_valid_for_ingest_with_only_invalid_data(
    invalid_test_vacancy_instances,
):
    """
    Verify that `valid_for_ingest` returns empty queryset when all data is invalid.
    """
    assert (
        len(invalid_test_vacancy_instances) > 0
    ), "Sanity check: should have invalid test vacancies"

    valid_vacancies = TestVacancies.objects_for_ingest.valid_for_ingest()

    assert not valid_vacancies.exists()


@pytest.mark.django_db
def test_vacancies_valid_for_ingest_empty_queryset():
    """
    Verify that `valid_for_ingest` works on empty queries.
    """
    empty_qs = TestVacancies.objects_for_ingest.filter(pk__isnull=True)
    filtered_qs = empty_qs.valid_for_ingest()

    assert not filtered_qs.exists()
