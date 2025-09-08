from enum import Enum
from typing import Optional

from django.db.models import F
from django.db.models import Max
from django.db.models import Min
from django.db.models import Value
from django.db.models.functions import Floor

"""
Base functions to perform diffs of records in OLEEO vs comparable JAO records.

These are used in the Managers, Querysets and Models.
"""


class SyncStatus(Enum):
    """
    Status of a record when comparing source and destination, using CRUD semantics.

    CREATE: Record exists in source but not in destination.
    READ: Record exists in both source and destination, and is unchanged.
    UPDATE: Record exists in both source and destination, but is changed.
    DELETE: Record only exists in destination.
    """

    CREATE = "create"
    READ = "read"
    """Read just means a record is unchanged, naming follows CRUD semantics."""
    UPDATE = "update"
    DELETE = "delete"


def get_buckets_modulo(qs, granularity_size=5000):
    """
    Splits a queryset into buckets using a single, efficient GROUP BY query.
    """
    # An initial check to avoid hitting the DB if the queryset is empty.
    if not qs.exists():
        return []

    # This single query does all the work on the database side.
    # 1. Annotate each row with a 'bucket_id' using integer division.
    # 2. Group the rows by that 'bucket_id'.
    # 3. For each group, calculate the MIN and MAX pk.
    buckets_query = (
        qs.annotate(
            bucket_id=Floor(F("pk") / Value(granularity_size))
        )
        .values("bucket_id")  # This acts as the GROUP BY clause
        .annotate(
            actual_min=Min("pk"),
            actual_max=Max("pk"),
        )
        .order_by("bucket_id") # Ensures results are in a predictable order
    )

    # The database returns a list of dictionaries; we reformat it to match the original.
    buckets = []
    for group in buckets_query:
        start_boundary = group["bucket_id"] * granularity_size
        end_boundary = start_boundary + granularity_size - 1
        buckets.append(
            (
                start_boundary,
                end_boundary,
                group["actual_min"],
                group["actual_max"],
            )
        )

    return buckets

def _build_pk_range_filter(
    pk_start: Optional[int] = None, pk_end: Optional[int] = None
):
    """
    Build primarty key filter kwargs to limit, used to limit a set of records to a subset.

    Note: It is expected that the records are already ordered by primary key.


    pk_start and pk_end must be None or integers, other kinds of primary key are unsupported.

    >>> _pk_limit_kwargs(None, None)
    {}

    >>> _pk_limit_kwargs(pk_start=100)
    {"pk__gte": 100)

    >>> _pk_limit_kwargs(pk_end=500)
    {"pk__lte": 500)

    >>> _pk_limit_kwargs(pkg_start=100, pk_end=500)
    {"pk__gte=100", "pk__lte": 500)
    """
    pk_filter_kwargs = {}
    if pk_start is not None:
        assert isinstance(pk_start, int), "Start of primary key range must be an int"
        pk_filter_kwargs["pk__gte"] = pk_start

    if pk_start is not None:
        assert isinstance(pk_start, int), "End of primary key range must be an int"
        pk_filter_kwargs["pk__lte"] = pk_end

    return pk_filter_kwargs


def iter_instances_diff(
    source_qs,
    destination_qs,
    include_create=True,
    include_read=True,
    include_update=True,
    include_delete=True,
):
    """
    Iterate through merged instances from two querysets, yielding tuples based on PK comparison.
    The input querysets should be ordered by pk, and ideally have the same range.

    Yields tuples of (SyncStatus, source_instance or None, dest_instance or None)

    SyncStatus can uses CRUD semantics:
    - SyncStatus.CREATE: source_instance exists, dest_instance is None
    - SyncStatus.DELETE: source_instance is None, dest_instance exists
    - SyncStatus.UPDATE: both instances exist, and source_instance indicates it needs update
    - SyncStatus.READ: both instances exist, and source_instance indicates no update needed

    Instances are compared using primary key.

    IMPORTANT: behaviour is undefined for queries not ordered by primary key.

    :param source_qs: Source queryset
    :param destination_qs: Destination queryset

    :param include_create: Include source-only instances (source_instance, None)
    :param include_delete: Include dest-only instances (None, dest_instance)
    :param include_update: Include changed matching instances (source_instance, dest_instance)
    :param include_read: Include unchanged matching instances (source_instance, dest_instance)

    :yield: (SyncStatus, source_instance or None, dest_instance or None)
    """
    assert (
        source_qs.model.get_destination_model() == destination_qs.model
    ), "self must be an upstream queryset of dest_qs"

    source_by_pk = source_qs.in_bulk()  # key=pk, value=instance
    del source_qs

    # Create an iterator over the pks of source.
    source_iter = iter([*source_by_pk.keys()])
    source_pk = next(source_iter, None)

    for dest_instance in destination_qs:
        # CREATE: Catch up source_pk to dest_instance.pk,
        # there are no destinations yet for these sources.
        while source_pk is not None and source_pk < dest_instance.pk:
            if include_create:
                yield SyncStatus.CREATE, source_by_pk.pop(source_pk), None
            source_pk = next(source_iter, None)

        if source_pk is None or source_pk > dest_instance.pk:
            # DELETE: dest exists but no matching source
            if include_delete:
                yield SyncStatus.DELETE, None, dest_instance
        elif source_pk == dest_instance.pk:
            # Matching items, have they changed ?
            source_instance = source_by_pk.pop(source_pk)
            if include_update or include_read:
                if source_instance.destination_requires_update(dest_instance):
                    if include_update:
                        yield SyncStatus.UPDATE, source_instance, dest_instance
                else:
                    if include_read:
                        yield SyncStatus.READ, source_instance, dest_instance
            source_pk = next(source_iter, None)

    # CREATE: Remaining source instances
    while source_pk is not None:
        if include_create:
            yield SyncStatus.CREATE, source_by_pk.pop(source_pk), None
        source_pk = next(source_iter, None)


def destination_pending_create_update_delete(
    source_model, destination_model, pk_start=None, pk_end=None, **kwargs
):
    """
    :return: source_qs: QuerySet, [new_source_instances...], [update_source_instances], deleted_qs: QuerySet

    Given a source and destination model that are comparable return:
    - source_qs: The source queryset (limited according to pk_start and pk_end and .valid_for_ingest())
    - a list of new instances to create in the destination
    - a list of existing instances to update in the destination
    - a queryset of instances to mark as deleted in the destination
    """

    pk_filter_kwargs = _build_pk_range_filter(pk_start, pk_end)
    source_qs = source_model.objects_for_ingest.order_by("pk").valid_for_ingest()
    if pk_filter_kwargs:
        source_qs = source_qs.filter(**pk_filter_kwargs)

    destination_qs = destination_model.objects.order_by("pk")
    if pk_filter_kwargs:
        destination_qs.filter(**pk_filter_kwargs)

    deleted_pks = []

    created_instances = []
    updated_instances = []
    delete_qs = destination_qs.none()

    # This method only deals with changed records:
    kwargs["include_read"] = False
    for status, source_instance, destination_instance in iter_instances_diff(
        source_qs, destination_qs, **kwargs
    ):
        if status == SyncStatus.UPDATE:
            assert source_instance is not None
            assert destination_instance is not None
            updated_instances.append(destination_instance)
        elif status == SyncStatus.CREATE:
            assert source_instance is not None
            assert destination_instance is None
            new_instance = destination_model(**source_instance.as_destination_dict())
            created_instances.append(new_instance)
        elif status == SyncStatus.DELETE:
            assert source_instance is None
            deleted_pks.append(destination_instance.pk)

    if deleted_pks:
        delete_qs = destination_qs.filter(pk__in=deleted_pks)

    return source_qs, created_instances, updated_instances, delete_qs
