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
def test_create_pending_from_simple_list(age_group_instances):
    """
    TestListAgeGroup is a simple list (reflecting ListAgeGroup), meaning that
    the data inside should be exactly copied to the destination model (AgeGroup).

    Verify that:

    Initially:  AgeGroup is not populated.
    Calling:    create_pending should populate agegroups.
    """
    expected_age_groups = {
        *TestListAgeGroup.objects.values_list("age_group_desc", flat=True)
    }

    assert expected_age_groups, "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists(), "Initially there should be no age groups"

    TestListAgeGroup.objects.create_pending()

    actual_age_groups = {*AgeGroup.objects.values_list("description", flat=True)}

    assert actual_age_groups == expected_age_groups


@pytest.mark.django_db
def test_create_pending_when_nothing_changed(age_group_instances):
    """
    Verify that:  update_pending does not change any records if row_last_updated is not changed.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    TestListAgeGroup.objects.create_pending()
    source_instances, destination_instances = TestListAgeGroup.objects.create_pending()

    assert AgeGroup.objects.count() == len(age_group_instances) > 1

    assert not source_instances.exists()
    assert destination_instances == []


@pytest.mark.django_db
def test_bulk_create_pending(age_group_instances):
    """
    Verify that bulk_create_pending correctly processes records in batches
    and yields the expected results for each batch.

    Since bulk_create_pending is a wrapper around create_pending, not all
    tests need to be duplicated.
    """
    # Initially, no destination records should exist
    assert not AgeGroup.objects.exists()

    batch_size = int(1 + len(age_group_instances) // 2)
    batch_results = list(
        TestListAgeGroup.objects.bulk_create_pending(max_batch_size=batch_size)
    )

    created_counts = [len(created_instances) for _, created_instances in batch_results]

    assert sum(created_counts) == len(
        age_group_instances
    ), f"Expected {len(age_group_instances)} total creates"

    assert created_counts[0] > 0, "Expected the first batch to contain creates"

    source_instances, created_instances = batch_results[0]

    assert isinstance(source_instances, QuerySet)
    assert isinstance(created_instances, list)
    assert created_instances
    assert source_instances.count() == len(created_instances)
    assert {type(created_instance) for created_instance in created_instances} == {
        AgeGroup
    }

    assert AgeGroup.objects.count() == len(age_group_instances)


@pytest.mark.django_db
def test_pending_create_no_destination_records(age_group_instances):
    """
    Verify that pending_create() returns all source records when no destination records exist.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    pending = TestListAgeGroup.objects.pending_create()

    source_pks = set(TestListAgeGroup.objects.values_list("pk", flat=True))
    pending_pks = set(pending.values_list("pk", flat=True))

    assert pending_pks == source_pks


@pytest.mark.django_db
def test_pending_create_after_sync(age_group_instances):
    """
    Verify that pending_create() returns empty queryset when all records already exist in destination.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    TestListAgeGroup.objects.create_pending()

    # Now no records should be pending creation
    pending = TestListAgeGroup.objects.pending_create()

    assert not pending.exists()


@pytest.mark.django_db
def test_pending_create_partial_sync(age_group_instances):
    """
    Verify that pending_create() returns only source records that don't exist in destination

    Simulating a partial sync.
    """
    instances_to_create = age_group_instances[:2]  # Create first 2
    assert len(instances_to_create) > 0

    destination_model = TestListAgeGroup.get_destination_model()
    for instance in instances_to_create:
        destination_model.objects.create(
            id=instance.pk,
            description=instance.age_group_desc,
            last_updated=instance.row_last_updated,
        )

    pending = TestListAgeGroup.objects.pending_create()
    assert pending.count() == len(age_group_instances) - len(instances_to_create)

    created_pks = {instance.pk for instance in instances_to_create}
    pending_pks = set(pending.values_list("pk", flat=True))
    source_pks = set(TestListAgeGroup.objects.values_list("pk", flat=True))

    expected_pending_pks = source_pks - created_pks
    assert pending_pks == expected_pending_pks


@pytest.mark.django_db
def test_pending_create_with_filtered_queryset(age_group_instances):
    """
    Verify that pending_create() works correctly when called on a filtered queryset.
    """
    assert len(age_group_instances) >= 2
    assert not AgeGroup.objects.exists()

    filtered_qs = TestListAgeGroup.objects.filter(
        pk__in=[age_group_instances[0].pk, age_group_instances[1].pk]
    )

    # Create one instance, which should leave one pending.
    first_instance = age_group_instances[0]
    AgeGroup.objects.create(
        id=first_instance.pk,
        description=first_instance.age_group_desc,
        last_updated=first_instance.row_last_updated,
    )

    pending_pks = filtered_qs.pending_create().values_list("pk", flat=True)

    assert {*pending_pks} == {age_group_instances[1].pk}


@pytest.mark.django_db
def test_pending_update_with_changes(age_group_instances):
    """
    Verify that pending_update() returns only records with newer row_last_updated.
    """
    # Create destination records
    TestListAgeGroup.objects.create_pending()

    # Update one source record
    expected_instance = age_group_instances[0]
    expected_instance.row_last_updated += timedelta(days=1)
    expected_instance.save()

    # Only the changed record should be pending update
    pending = TestListAgeGroup.objects.pending_update()
    assert pending.count() == 1
    assert pending.first().pk == expected_instance.pk


@pytest.mark.django_db
def test_update_pending_when_nothing_changed(age_group_instances):
    """
    Verify that:  update_pending does not change any records if row_last_updated is not changed.
    """
    TestListAgeGroup.objects.create_pending()
    assert AgeGroup.objects.count() == len(age_group_instances)

    source_instances, destination_instances, updated = (
        TestListAgeGroup.objects.update_pending()
    )

    assert not source_instances.exists()
    assert destination_instances == []
    assert updated is 0


@pytest.mark.django_db
def test_update_pending_after_changes(age_group_instances):
    """
    Verify that:  update_pending does not change any records if row_last_updated is not changed.
    """
    TestListAgeGroup.objects.create_pending()
    assert AgeGroup.objects.count() == len(age_group_instances)

    # Initially, no updates should be pending.
    assert TestListAgeGroup.objects.update_pending()[2] is 0

    # Push row_last_updated forward on a source record to simulate a change
    # and trigger an update.
    expected_instance = age_group_instances[0]

    expected_instance.row_last_updated += timedelta(days=1)
    expected_instance.save()
    expected_instance.refresh_from_db()

    # One record should be updated.
    source_updated, destination_updated, updated_count = (
        TestListAgeGroup.objects.update_pending()
    )
    expected_instance.refresh_from_db()

    assert updated_count == 1
    assert source_updated.count() == updated_count
    assert len(destination_updated) == updated_count

    source_age_group = source_updated.first()
    destination_age_group = destination_updated[0]

    assert source_age_group == expected_instance

    # Verify fields were updated.
    assert source_age_group.age_group_desc == destination_age_group.description
    assert source_age_group.row_last_updated == destination_age_group.last_updated


@pytest.mark.django_db
def test_bulk_update_pending(age_group_instances):
    """
    Verify that bulk_update_pending correctly processes records in batches
    and yields the expected results for each batch.

    Since bulk_update_pending is a wrapper around update_pending, not all
    tests need to be duplicated.
    """
    TestListAgeGroup.objects.create_pending()
    assert AgeGroup.objects.count() == len(age_group_instances)

    # Initially, no updates should be pending
    assert TestListAgeGroup.objects.update_pending()[2] == 0

    # Update just one record to trigger an update
    expected_instance = age_group_instances[0]
    expected_instance.row_last_updated += timedelta(days=1)
    expected_instance.save()
    expected_instance.refresh_from_db()

    # Set the batch size so the results are in two batches.
    batch_size = int(1 + len(age_group_instances) // 2)
    batch_results = list(
        TestListAgeGroup.objects.bulk_update_pending(max_batch_size=batch_size)
    )

    updated_counts = [updated_count for _, _, updated_count in batch_results]

    assert len(batch_results) == 2
    assert updated_counts == [1, 0], "Expected the first batch to contain the update"

    # Now we've verified the update is in the first batch,
    # check that the content is what we expect.
    source_instances, destination_instances, updated_count = batch_results[0]

    assert isinstance(source_instances, QuerySet)
    assert isinstance(destination_instances, list)
    assert isinstance(updated_count, int)

    assert source_instances.count() == updated_count == 1
    assert len(destination_instances) == updated_count == 1

    source_age_group = source_instances.first()
    destination_age_group = destination_instances[0]

    assert source_age_group == expected_instance
    assert isinstance(destination_age_group, AgeGroup)

    assert source_age_group.age_group_desc == destination_age_group.description
    assert source_age_group.row_last_updated == destination_age_group.last_updated


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
        *TestListAgeGroup.objects.filter(pk=source_instance.pk).as_destination_values()
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
        TestListAgeGroup.objects.filter(pk=source_instance.pk).as_destination_values(
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
def test_as_destination_query_synchronized(age_group_instances):
    """
    Verify that as_destination_query() works when source and destination are synchronized.
    """
    TestListAgeGroup.objects.create_pending()

    destination_qs = TestListAgeGroup.objects.as_destination_filter()

    assert destination_qs.count() == len(age_group_instances)
    assert destination_qs.model == AgeGroup


@pytest.mark.django_db
def test_as_destination_query_not_synchronized(age_group_instances):
    """
    Verify that as_destination_query() raises error when not synchronized (strict=True).
    """
    with pytest.raises(ValueError, match=r"\d+ != \d+, lists are not synchronized"):
        TestListAgeGroup.objects.as_destination_filter(strict=True)


@pytest.mark.django_db
def test_as_destination_query_not_strict(age_group_instances):
    """
    Verify that as_destination_query() works with strict=False even when not synchronized.
    """
    destination_qs = TestListAgeGroup.objects.as_destination_filter(strict=False)
    assert destination_qs.count() == 0  # No destination records exist


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
        *TestListAgeGroup.objects.filter(
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
        *TestListAgeGroup.objects.filter(
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
        *TestListAgeGroup.objects.filter(pk__in=expected_pks).values_list(
            "age_group_desc", flat=True
        )
    ]

    destination_instances = [
        *TestListAgeGroup.objects.filter(pk__in=expected_pks).as_destination_instances()
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
        *TestListAgeGroup.objects.none().as_destination_instances()
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

    destination_instances = [*TestListAgeGroup.objects.as_destination_instances()]
    AgeGroup.objects.bulk_create(destination_instances)

    actual_pks = set(AgeGroup.objects.values_list("pk", flat=True))

    assert actual_pks == expected_pks


@pytest.mark.django_db
def test_destination_pending_create(age_group_instances):
    """
    Verify that destination_pending_create() returns generator of instances pending creation.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"
    assert not AgeGroup.objects.exists()

    expected_pks = {instance.pk for instance in age_group_instances}

    source_instances, destination_instances = (
        TestListAgeGroup.objects.destination_pending_create()
    )

    # destination_instances starts as a generator, so make it a list
    destination_instances = list(destination_instances)

    actual_pks = {inst.id for inst in destination_instances}

    assert actual_pks == expected_pks
    assert all(isinstance(inst, AgeGroup) for inst in destination_instances)
    assert len(source_instances) == len(destination_instances)


@pytest.mark.django_db
def test_destination_pending_update(age_group_instances):
    """
    Verify that destination_pending_update() returns queryset of instances pending update.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    TestListAgeGroup.objects.create_pending()

    # Updating the row_last_updated should make it pending update.
    source_instance = age_group_instances[0]
    source_instance.row_last_updated += timedelta(days=1)
    source_instance.save()

    pending, destination_qs = TestListAgeGroup.objects.destination_pending_update()
    actual_pks = set(destination_qs.values_list("pk", flat=True))

    assert destination_qs.model == AgeGroup
    assert pending.count() == 1
    assert pending[0].pk == source_instance.pk
    assert actual_pks == {source_instance.pk}


@pytest.mark.django_db
def test_destination_pending_delete(age_group_instances):
    """
    Verify that destination_pending_delete() returns queryset of instances pending deletion.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    TestListAgeGroup.objects.create_pending()

    # Delete one source record to trigger pending delete
    source_instance = age_group_instances[0]

    # Grab pk before delete will unsets it.
    expected_pk = source_instance.pk
    source_instance.delete()

    destination_qs = TestListAgeGroup.objects.destination_pending_delete()

    actual_pks = set(destination_qs.values_list("pk", flat=True))

    assert destination_qs.model == AgeGroup
    assert actual_pks == {expected_pk}


@pytest.mark.django_db
def test_delete_pending(age_group_instances):
    """
    Verify that delete_pending() deletes records that exist in destination but not in source.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    TestListAgeGroup.objects.create_pending()
    assert AgeGroup.objects.count() == len(age_group_instances)

    # Delete one source record to trigger pending delete
    source_instance = age_group_instances[0]
    expected_pk = source_instance.pk
    source_instance.delete()

    deleted_count = TestListAgeGroup.objects.delete_pending()

    assert deleted_count == 1
    assert not AgeGroup.objects.filter(pk=expected_pk).exists()
    assert AgeGroup.objects.count() == len(age_group_instances) - 1


@pytest.mark.django_db
def test_delete_pending(age_group_instances):
    """
    Verify that delete_pending() deletes records that exist in destination but not in source.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    TestListAgeGroup.objects.create_pending()
    pks_before = set(AgeGroup.objects.values_list("pk", flat=True))

    # Delete one source record to trigger pending delete
    source_instance = age_group_instances[0]
    expected_deleted_pk = source_instance.pk
    source_instance.delete()

    deleted_count, _ = TestListAgeGroup.objects.delete_pending()
    pks_after = set(AgeGroup.objects.values_list("pk", flat=True))

    assert deleted_count == 1
    assert pks_before - pks_after == {expected_deleted_pk}


@pytest.mark.django_db
def test_update_deletion_marks(age_group_instances):
    """
    Verify that mark_delete_pending() marks records as deleted instead of actually deleting them.
    """
    assert (
        len(age_group_instances) > 0
    ), "Sanity check: age_group_instances should be populated"

    TestListAgeGroup.objects.create_pending()

    # Delete a source record and verify it appears as a pending delete
    source_instance = age_group_instances[0]
    expected_marked_pk = source_instance.pk
    source_instance.delete()

    deleted_count, undeleted_count = TestListAgeGroup.objects.update_deletion_marks()
    marked_deleted_pks = set(
        AgeGroup.objects.filter(is_deleted=True).values_list("pk", flat=True)
    )

    assert undeleted_count == 0
    assert deleted_count == 1
    assert marked_deleted_pks == {expected_marked_pk}


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
        *TestListAgeGroup.objects.filter(
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
        *TestListAgeGroup.objects.filter(
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

    original_qs = TestListAgeGroup.objects.all()
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
        TestVacancies.objects.count() == total_count
    ), "Sanity check: all test vacancies created"

    valid_pks = set(
        TestVacancies.objects.valid_for_ingest().values_list("pk", flat=True)
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

    all_vacancies_pks = set(TestVacancies.objects.values_list("vacancy_id", flat=True))
    valid_vacancies_pks = set(
        TestVacancies.objects.valid_for_ingest().values_list("vacancy_id", flat=True)
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

    valid_vacancies = TestVacancies.objects.valid_for_ingest()

    assert not valid_vacancies.exists()


@pytest.mark.django_db
def test_vacancies_valid_for_ingest_empty_queryset():
    """
    Verify that `valid_for_ingest` works on empty queries.
    """
    empty_qs = TestVacancies.objects.filter(pk__isnull=True)
    filtered_qs = empty_qs.valid_for_ingest()

    assert not filtered_qs.exists()
