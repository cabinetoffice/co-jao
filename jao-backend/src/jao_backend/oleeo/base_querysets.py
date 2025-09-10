"""
QuerySets generically based around syncing data from an upstream data source.
"""

from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from cachemethod import lru_cachemethod
from django.db import models
from djantic import ModelSchema

from jao_backend.ingest.ingester.schema_registry import get_model_transform_schema

import logging

logger = logging.getLogger(__name__)


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
        :return: list of the keys, if one of the keys is 'pk' replace with the actual primary key name.

        Django accepts 'pk' as whatever the primary key is.

        In the intermediate transform, pydantic is used which needs exact key names.

        Note:   While pk is transformed, keys that follow relationships (e.g. "vacancy__pk") are not transformed,
                so cannot be used.
        """
        pk_name = model._meta.pk.name  # noqa
        return [pk_name if k == "pk" else k for k in keys]

    @lru_cachemethod(maxsize=1)
    def _get_destination_model(self):
        return self.model.get_destination_model()

    @lru_cachemethod(maxsize=1)
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

        transform = get_model_transform_schema(destination_model)
        destination_field = self._get_alias_or_field(transform, source_field)

        return destination_field

    @lru_cachemethod(maxsize=1)
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

    def _transform_value(
        self, value: Dict[str, Any], *args, destination_fields: Optional[List] = None
    ) -> Dict[str, Any]:
        """\
        Transform a single source record value (as returned by .values) to a destination model values.

        :param value: Dictionary representing a single source record
        :param args: keys in the destination column to include.
        :param destination_fields: optional list of fields to include
        :return: Dictionary transformed to represent the destination model instance.
        """
        if destination_fields:
            destination_fields = self._resolve_pk_fields(self.model, destination_fields)
        else:
            destination_fields = {}

        destination_model = self._get_destination_model()
        transform: Type[ModelSchema] = get_model_transform_schema(destination_model)

        include = self._resolve_pk_fields(destination_model, args) if args else None

        return {
            **{
                f"source_{source_field}": value[source_field]
                for source_field in destination_fields
            },
            **transform(**value).model_dump(include=include),
        }

    def as_destination_values(
        self, *args, destination_fields: Optional[List] = None
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
        :param destination_fields: optional list of fields to include (to use a source field name prefix with "source_").
        :return: A list of dictionaries transformed to represent the destination model instances.
        """
        return (
            self._transform_value(value, *args, destination_fields=destination_fields)
            for value in self.values()
        )

    def as_destination_values_list(
        self,
        *args,
        flat=False,
        destination_fields: Optional[List] = None,
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
        :param destination_fields: Optional list of fields to include (to use a source field name prefix with source_).
        :param flat: If True, return single values instead of 1-tuples.
        :return: A generator yielding tuples (or single values if flat=True) representing the destination model values.
        """
        if flat and destination_fields:
            raise ValueError("When flat=True, source_fields cannot be specified.")

        # This attempts to adhere to the same interface as values_list() but may not be complete
        # where functionality is not required.
        destination_values = self.as_destination_values(
            *args, destination_fields=destination_fields
        )

        if flat:
            if len(args) != 1:
                raise ValueError("When flat=True, only one field is allowed.")

            for value in destination_values:
                yield list(value.values())[0]
        else:
            for value in destination_values:
                yield tuple(value.values())

    def as_destination_instances(
        self, batch_size: Optional[int] = None
    ) -> Generator[models.Model, None, None]:
        """\
        :param batch_size: If specified, process the queryset in batches of this size
        :return:  Generator of destination model instances populated with data from this queryset.

        The model instances returned are not guaranteed to be backed by records in the database.

        ** IMPORTANT **

        This is intended to be used with bulk_create(),
        .as_destination_query() is a better choice in most instances the instances it returns are
        from the database.
        """
        destination_model = self._get_destination_model()

        if batch_size is None:
            for value in self.as_destination_values():
                yield destination_model(**value)
            return

        # Passing batch_size can take pressure off the source database,
        # to do that iterate over the records from it using a set chunk_size
        # and convert as we go.
        for source_record in self.values().iterator(chunk_size=batch_size):
            # Transform each source record directly without additional queries
            transformed_value = self._transform_value(source_record)
            yield destination_model(**transformed_value)
