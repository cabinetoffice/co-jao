"""
QuerySets generically based around syncing data from an upstream data source.
"""

from functools import lru_cache
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Self
from typing import Tuple
from typing import Type
from typing import Union

from django.db import models
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils import timezone
from djantic import ModelSchema

from jao_backend.ingest.ingester.schema_registry import get_upstream_schema_for_model


def sliding_window_range(
    source_start, source_end, max_batch_size, extra, progress_bar=None
):
    """
    Sliding window.

    Used to iterate over primary keys, that aren't expected to be contiguous.

    start adds max_batch_size, end is max_batch_size + extra
    """
    if not progress_bar:
        progress_bar = lambda x: x

    for batch_start in progress_bar(range(source_start, source_end, max_batch_size)):
        # Sliding window over the source data ids, to limit the amount of data being compared
        # This is slightly bigger than max_batch_size as the ids in the database are not contiguous,
        batch_end = batch_start + max_batch_size + extra

        yield batch_start, batch_end


class UpstreamModelQuerySet(models.QuerySet):
    """
    Provide methods to support create, update and delete bulk updates from lists in OLEEO/R2D2
    to JAO.

    Models that extend ListModelBase have a default manager that return ListModelQuerySet.
    """

    @staticmethod
    def _resolve_pk_fields(model, keys):
        """
        :return a list of the keys, if one of the keys is 'pk' replace with the actual primary key name.

        Django accepts 'pk' as whatever the primary key is.

        In the intermediate transform, pydantic is used which needs exact key names.

        Note:   While pk is transformed, keys that follow relationships (e.g. "vacancy__pk") are not transformed,
                so cannot be used.
        """
        pk_name = model._meta.pk.name  # noqa
        return [pk_name if k == "pk" else k for k in keys]

    @lru_cache(maxsize=1)
    def _get_destination_model(self):
        return self.model.get_destination_model()

    @lru_cache(maxsize=1)
    def _get_alias_or_field(self, transform, name):
        """
        Utility function to find a field or alias in the transform model fields.

        Transform is a pydantic model schema that represents the upstream schema for a Django model,
        field renames are specified using aliases.

        :param transform: The transform model schema.
        """

        # Django supports a generic "pk" field, which needs resolving before
        # passing to pydantic.
        if name == "pk":
            name = self.model._meta.pk.name  # noqa

        if name in transform.model_fields:
            return name

        for field_name, field_info in transform.model_fields.items():
            if field_info.alias == name:
                return field_name

        raise ValueError(f"Field '{name}' not found in transform model fields.")

    def _get_destination_field_name(self, source_field) -> str:
        """
        :return: field from destination that matches the source ingest field.

        This is only used when a single field is needed, in most cases it's
        better to directly use the transform, which makes it easy to do more
        than one operation at a time (e.g. renames / mapping).
        """
        destination_model = self._get_destination_model()

        transform = get_upstream_schema_for_model(destination_model)
        destination_field = self._get_alias_or_field(transform, source_field)

        return destination_field

    @lru_cache(maxsize=1)
    def _get_id_fields(self):
        """
        :return : A tuple of the source and destination unique id fields.

        These id fields are used to match source and destination records.
        """
        id_field = self.model.get_ingest_unique_id_field()
        dest_id_field = self._get_destination_field_name(id_field)
        return id_field, dest_id_field

    def valid_for_ingest(self):
        """
        Subclasses can use this to filter out known bad data.
        """
        return self

    def as_destination_values(
        self, *args, source_fields: Optional[List] = None
    ) -> Iterable[Dict[str, Any]]:
        """\
        Calls `self.values()` and generates dictionaries transformed to represent destination model values.

        This is intended to use with bulk operations such as bulk_create, bulk_update, etc.

        The destination model is found by calling get_destination_model()

        The schema for the transformation is found in the schema_registry and looked up using
        get_upstream_schema_for_model.

        source fields can be added to the output by specifying them in the source_fields argument,
        source fields are prefixed with "source_" to avoid name collisions with destination fields.

        :param args: keys in the destination column to include.
        :param source_fields: optional list of fields to include from the source model.
        :return: A list of dictionaries transformed to represent the destination model instances.
        """
        if source_fields:
            source_fields = self._resolve_pk_fields(self.model, source_fields)
        else:
            source_fields = {}

        destination_model = self._get_destination_model()
        transform: Type[ModelSchema] = get_upstream_schema_for_model(destination_model)

        include = self._resolve_pk_fields(destination_model, args) if args else None

        # Generate dicts including the transformed values (see the transform line),
        # and any source fields (prefixed with "source_") that were specified in
        # the source_fields parameter.
        #
        # This is used in operations that require mappings between source and destination
        #
        # Note: a pydantic validation error here may mean that fields were not specified in
        #       the upstream schema.
        #       This can happen when fields were added to a model, but not the schema.
        return (
            {
                **{
                    f"source_{source_field}": value[source_field]
                    for source_field in source_fields
                },
                **transform(**value).model_dump(include=include),
            }
            for value in self.values()
        )

    def as_destination_values_list(
        self,
        *args,
        flat=False,
        source_fields: Optional[List] = None,
    ) -> Generator[Union[Tuple, Any], None, None]:
        """\
        Equivalent to .values_list: query the List model and transform the results to the destination model
        using `.as_destination_values().`

        Calls *`self.values_list()`* and generates tuples transformed to represent destination model values.

        Limitations:
        - Argument names are those of the destination model, but do not follow relationships:
        "pk" will work, but "vacancy__pk" will not.
        - Named Tuples output is not implemented.
        - The values are not guaranteed to match records in the destination table.

        :param args: The fields to include in the values (using the destination model names or "pk")
        :param source_fields: Optional list of fields to include from the source model.
        :param flat: If True, return single values instead of 1-tuples.
        :return: A generator yielding tuples (or single values if flat=True) representing the destination model values.
        """
        if flat and source_fields:
            raise ValueError("When flat=True, source_fields cannot be specified.")

        # This attempts to adhere to the same interface as values_list() but may not be complete
        # where functionality is not required.
        destination_values = self.as_destination_values(
            *args, source_fields=source_fields
        )

        if flat:
            if len(args) != 1:
                raise ValueError("When flat=True, only one field is allowed.")

            for value in destination_values:
                yield list(value.values())[0]
        else:
            for value in destination_values:
                yield tuple(value.values())

    def as_destination_instances(self) -> Generator[models.Model, None, None]:
        """\
        :return: A generator of destination model instances populated with daa from this queryset.

        The model instances returned are not guaranteed to be backed by records in the database.

        This is intended to be used with bulk_create().

        .as_destination_query() is a better choices in most instances the instances it returns are
        from the database.
        """
        destination_model = self._get_destination_model()
        destination_values = self.as_destination_values()
        return (destination_model(**value) for value in destination_values)

    def as_destination_filter(self, strict=True) -> QuerySet[models.Model]:
        """\
        :return: A queryset of destination model instances populated with data
        from this queryset.

        :param strict: If True, raise an error if the source and destination don't contain the same records.
        """
        destination_model = self._get_destination_model()

        id_field, dest_id_field = self._get_id_fields()

        destination_ids = [*self.as_destination_values_list(dest_id_field, flat=True)]

        destination_qs = destination_model.objects.filter(
            **{f"{dest_id_field}__in": destination_ids}
        )

        source_count = len(destination_ids)
        destination_count = destination_qs.count()

        if strict and (source_count != destination_count):
            raise ValueError(
                f"{source_count} != {destination_count}, lists are not synchronized."
            )

        return destination_qs

    def pending_create(self) -> Self:
        """
        :return: List records that exist in this queryset but not in the destination model.
        """
        id_field, dest_id_field = self._get_id_fields()

        destination_model = self._get_destination_model()

        # During comparison source_ids are needed, during querying destination_ids are needed.
        # Create a dict mapping dest_id to source_id from the current queryset
        source_ids = {
            value[dest_id_field]: value[f"source_{id_field}"]
            for value in self.as_destination_values(
                dest_id_field, source_fields=[id_field]
            )
        }

        destination_ids = set(
            destination_model.objects.values_list(dest_id_field, flat=True)
        )

        new_ids = set(source_ids.keys()) - destination_ids
        new_source_ids = [source_ids[new_id] for new_id in new_ids]
        return self.filter(**{f"{id_field}__in": new_source_ids})

    def pending_update(self) -> Self:
        """
        :return: List records that where the id matches but the update time differs from the destination model.
        """
        destination_model = self._get_destination_model()

        # Get the name of the last_updated field in the destination, this is used later
        # to compare rows.
        dest_last_updated_field = self._get_destination_field_name(
            self.model.ingest_last_updated_field
        )

        id_field, dest_id_field = self._get_id_fields()
        source_data = dict(
            self.as_destination_values_list(dest_id_field, dest_last_updated_field)
        )
        destination_data = dict(
            destination_model.objects.values_list(
                dest_id_field, dest_last_updated_field
            )
        )

        common_pks = set(source_data.keys()) & set(destination_data.keys())

        ids_to_update = [
            source_pk
            for source_pk in common_pks
            if source_data[source_pk] != destination_data[source_pk]
        ]

        return self.filter(**{f"{id_field}__in": ids_to_update})

    def pending_delete(self):
        """
        It's not possible to implement pending_delete, since it would have
        to return records that exist in the destination model but not in this queryset.\

        This stub is here, since the user may expect to see `pending_delete` after the other pending functions.
        """
        raise NotImplementedError(
            "pending_delete is not implemented for UpstreamModelQuerySet. "
            "Use destination_pending_delete() instead."
        )

    def destination_pending_create(
        self, max_batch_size: Optional[int] = None
    ) -> Tuple[Self, Generator[models.Model, None, None]]:
        """
        :param max_batch_size: The maximum number of records to return.
        :return: tuple of `source_instances, destination_instances`

        source_instances is a query on the source model up to max_batch_size items.
        destination_instances is a generator of Instances in the destination model matching this queryset that are pending creation.
        """
        pending: Self = self.pending_create()
        if max_batch_size:
            pending = pending[:max_batch_size]
        return pending, pending.as_destination_instances()

    def destination_pending_update(
        self, max_batch_size: Optional[int] = None
    ) -> Tuple[Self, Self]:
        """
        :param max_batch_size: The maximum number of records to return.
        :return: tuple of `source_instances, destination_instances`

        source_instances is this queryset, truncated to max_batch_size (if specified).
        destination_instances are the equivalent records in the destination model, see `as_destination_filter` for more information.
        """
        pending: Self = self.pending_update()
        if max_batch_size:
            pending = pending[:max_batch_size]
        return pending, pending.as_destination_filter()

    def destination_pending_delete(self) -> Self:
        """
        :return: tuple of `source_instances, destination_pending`

        :destination_pending are the records in the destination model that are pending deletion.

        Note:  This triggers a full table query over the source model, since the criteria
        for deletion is that the record exists in the destination model but not in this queryset,
        so no existing filters on the query could apply.
        """
        destination_model = self._get_destination_model()
        id_field, dest_id_field = self._get_id_fields()
        valid_objects = self.model.objects.valid_for_ingest()

        if not valid_objects.exists():
            return destination_model.objects.none()

        source_ids = valid_objects.as_destination_values_list(dest_id_field, flat=True)

        destination_pending = destination_model.objects.all().exclude(
            **{f"{dest_id_field}__in": source_ids}
        )

        return destination_pending

    def create_pending(
        self, max_batch_size: Optional[int] = None
    ) -> Tuple[Self, List[models.Model]]:
        """
        Bulk create records that exist in this queryset but not in the destination model.

        :return: tuple of (source_instances, destination_instances)

        source_instances is this query, truncated to max_batch_size if specified.
        destination_instances is a list of created instances, as output by djangos `bulk_create`.
        """
        destination_model = self._get_destination_model()
        source_instances, destination_instances = self.destination_pending_create(
            max_batch_size=max_batch_size
        )

        return (
            source_instances,
            destination_model.objects.bulk_create(
                destination_instances, batch_size=max_batch_size
            ),
        )

    @atomic
    def update_pending(
        self, max_batch_size: Optional[int] = None
    ) -> Tuple[Self, List[models.Model], Any]:
        """
        Bulk update records in this queryset that exist in the destination model.

        :return: tuple of `source_instances, destination_instances, amount_updated`

        source_instances is a query on the source model up to max_batch_size items.
        destination_instances A list of updated destination instances (as passed to `bulk_update`).
        amount_updated is the amount of records updated in the destination model (see Djangos `bulk_update`)
        """
        destination_model = self._get_destination_model()
        destination_fields = [
            field.name
            for field in destination_model._meta.fields
            if field.name != "id"  # noqa
        ]

        pending = self.pending_update()
        destination_instances = [*pending.as_destination_instances()]

        updated_count = destination_model.objects.bulk_update(
            destination_instances, destination_fields, batch_size=max_batch_size
        )

        return pending, destination_instances, updated_count

    @atomic
    def bulk_create_pending(self, max_batch_size=10000, append=True, progress_bar=None):
        """
        Batch create pending records.

        This is intended for larger, non-list tables such as Vacancies.

        This method uses a sliding window over the id fields, as a restriction
        it can only be used where the id fields are contiguous and numeric.

        Generates tuples of (source_instances, created_instances), from `create_pending`
        """
        id_field, dest_id_field = self._get_id_fields()

        if append:
            dest_model = self.model.get_destination_model()
            source_start = getattr(
                dest_model.objects.order_by(dest_id_field).last(), dest_id_field, 0
            )
        else:
            source_start = 0

        source_end = getattr(self.last(), id_field, 0)

        if source_start == self.last():
            return

        # IDs are not contiguous query more from the source model than the max_batch_size
        extra = 50 + (max_batch_size // 10)
        for source_start, source_end in sliding_window_range(
            source_start, source_end, max_batch_size, extra, progress_bar=progress_bar
        ):
            source_instances, created_instances = self.filter(
                **{f"{id_field}__gte": source_start, f"{id_field}__lte": source_end}
            ).create_pending(max_batch_size=max_batch_size)
            yield source_instances, created_instances

    def bulk_update_pending(self, max_batch_size=10000, progress_bar=None):
        """
        Batch create pending records.

        This is intended for larger, non-list tables such as Vacancies.

        This method uses a sliding window over the id fields, as a restriction
        it can only be used where the id fields are contiguous and numeric.

        Generates tuples of (pending, destination_instances, updated_count), from
        `update_pending`
        """
        id_field, _ = self._get_id_fields()
        source_start = getattr(self.first(), id_field)
        source_end = getattr(self.last(), id_field)

        if source_end == self.last():
            return

        for batch_start, batch_end in sliding_window_range(
            source_start, source_end, max_batch_size, 0, progress_bar=progress_bar
        ):
            source_instances, destination_instances, updated_count = self.filter(
                **{f"{id_field}__gte": batch_start, f"{id_field}__lte": batch_end}
            ).update_pending(max_batch_size=max_batch_size)
            yield source_instances, destination_instances, updated_count

    def delete_pending(self) -> int:
        """
        Delete records that exist in the destination model but not in this queryset.
        """
        destination_instances = self.destination_pending_delete()
        return destination_instances.delete()

    def update_deletion_marks(self) -> tuple[int, int]:
        """
        Mark models for deletion in the destination model.
        """
        destination_model = self._get_destination_model()
        pending_delete = self.destination_pending_delete()
        _, dest_id_field = self._get_id_fields()

        pending_undelete = destination_model.objects.filter(is_deleted=True).exclude(
            **{
                f"{dest_id_field}__in": pending_delete.values_list(
                    dest_id_field, flat=True
                )
            }
        )

        now = timezone.now()
        return (
            pending_delete.update(is_deleted=True, last_updated=now),
            pending_undelete.update(is_deleted=False, last_updated=now),
        )
