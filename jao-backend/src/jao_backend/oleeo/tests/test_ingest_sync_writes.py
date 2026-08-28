"""
Regression tests for the write side of upstream synchronisation.

`iter_instances_diff` decided correctly which records had changed, but two of the three
branches that act on that decision were wrong:

- UPDATE returned the untouched destination row, so bulk_update wrote every column back
  to the value it already held and upstream changes never landed.
- DELETE cleared `is_deleted` instead of setting it, so records withdrawn upstream stayed
  visible to consumers that filter on that column.

Both failed silently, hence these tests.
"""

from datetime import timedelta

import pytest

from jao_backend.application_statistics.models import AgeGroup
from jao_backend.ingest.ingester.ingest_vacancies import OleeoVacanciesIngest
from jao_backend.oleeo.tests.fixtures import age_group_instances  # noqa: F401
from jao_backend.oleeo.tests.fixtures import age_group_list_data  # noqa: F401
from jao_backend.oleeo.tests.fixtures import enable_oleeo_db  # noqa: F401
from jao_backend.oleeo.tests.models import TestListAgeGroup


def sync_create():
    """
    Run the create half of a sync, leaving the destination matching the source.

    Both tests need a populated destination before they can exercise update/delete.
    """
    _, create_instances, _, _ = TestListAgeGroup.destination_pending_sync()
    AgeGroup.objects.bulk_create(create_instances)
    return create_instances


@pytest.mark.django_db
def test_update_carries_upstream_values(age_group_instances):  # noqa: F811
    """A changed upstream value must reach the instance handed to bulk_update."""
    sync_create()

    source = TestListAgeGroup.objects_for_ingest.get(pk=2)
    source.age_group_desc = "25-29 (revised)"
    source.row_last_updated += timedelta(days=1)
    source.save()

    _, _, update_instances, _ = TestListAgeGroup.destination_pending_sync()

    assert [instance.pk for instance in update_instances] == [2]
    # Without apply_source_values these assertions get the pre-change values.
    assert update_instances[0].description == "25-29 (revised)"
    assert update_instances[0].last_updated == source.row_last_updated


@pytest.mark.django_db
def test_update_leaves_unchanged_records_alone(age_group_instances):  # noqa: F811
    """Only records whose last updated timestamp moved should be pending update."""
    sync_create()

    _, _, update_instances, _ = TestListAgeGroup.destination_pending_sync()

    assert update_instances == []


@pytest.mark.django_db
def test_delete_marks_destination_as_deleted(age_group_instances):  # noqa: F811
    """A record removed upstream must be flagged is_deleted, not un-flagged."""
    ingester = OleeoVacanciesIngest(batch_size=100)
    ingester._ingest_model(TestListAgeGroup, AgeGroup)

    total = AgeGroup.objects.count()
    assert total, "destination should be populated before testing deletion"
    assert not AgeGroup.objects.filter(is_deleted=True).exists()

    TestListAgeGroup.objects_for_ingest.filter(pk=3).delete()
    ingester._ingest_model(TestListAgeGroup, AgeGroup)

    # This used to be update(is_deleted=False), which left withdrawn records visible
    # to every consumer filtering on is_deleted (e.g. the MCP search lambda).
    assert AgeGroup.objects.get(pk=3).is_deleted is True
    assert AgeGroup.objects.filter(is_deleted=False).count() == total - 1
