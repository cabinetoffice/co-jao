from functools import lru_cache
from typing import Type, Union, Tuple, Iterable, Dict, Any, Generator, Self, List, Optional

from django.utils import timezone
from django.db import models
from django.db.models import QuerySet, Q
from djantic import ModelSchema

from jao_backend.common.querysets import SqlServerIsValidDecimal, SqlServerIsValidDecimalOrNull
from jao_backend.oleeo.ingest_schemas.oleeo_schema_registry import get_oleeo_schema_for_model

def sliding_window_range(source_start, source_end, max_batch_size, extra, progress_bar=None):
    """
    Sliding window.

    Used to iterate over primary keys, that aren't expected to be contiguous.

    start adds max_batch_size, end is max_batch_size + extra
    """
    if not progress_bar:
        progress_bar = lambda x: x

    for batch_start in progress_bar(range(source_start, source_end, max_batch_size)):
        # Sliding window over the source data pks, to limit the amount of data being compared
        # This is slightly bigger than max_batch_size as the ids in the database are not contiguous,
        batch_end = batch_start + max_batch_size + extra

        yield batch_start, batch_end

#
# class JaoAppsQuerySet(models.QuerySet):
#     def annotate_age_groups(self, age_groups=None):
#         """
#         Annotate the queryset with counts for each age group.
#
#         Args:
#             age_groups: List of age group strings. If None, a default list will be used.
#
#         Returns:
#             The queryset with age group annotations added
#         """
#         # Define default age groups if none provided
#         if age_groups is None:
#             age_groups = ['16-24', '25-29', '30-34', '35-39',
#                           '40-44', '45-49', '50-54', '55-59', '60-64', '65+']
#
#         # Build dynamic annotations for each age group
#         annotations = {}
#         for age_group in age_groups:
#             # Create a valid Python identifier for the field name
#             field_name = f'age_group_{age_group.replace("-", "_").replace("+", "plus").replace(" ", "_").lower()}'
#
#             # Create the annotation for this age group
#             annotations[field_name] = Count(
#                 Case(
#                     When(age_group_desc=age_group, then=1),
#                     default=0,
#                     output_field=IntegerField()
#                 )
#             )
#
#         # Apply all annotations to the queryset
#         return self.annotate(**annotations)


class UpstreamModelQuerySet(models.QuerySet):
    """
    Provide methods to support create, update and delete bulk updates from lists in OLEEO/R2D2
    to JAO.

    Models that extend ListModelBase have a default manager that return ListModelQuerySet.
    """

    @staticmethod
    def _parse_keys(model, keys):
        """
        Allow the user to use 'pk' as a shortcut for the primary key field name.
        """
        pk_name = model._meta.pk.name  # noqa
        return [pk_name if k == 'pk' else k for k in keys]

    @lru_cache(maxsize=1)
    def _get_destination_model(self):
        return self.model.get_destination_model()

    def exclude_known_bad(self):
        """
        Subclasses can use this to filter out known bad data.
        """
        return self

    def as_destination_values(self, *args) -> Iterable[Dict[str, Any]]:
        """\
        Calls `self.values()` and generates dictionaries transformed to represent destination model values.

        This is intended to use with bulk operations such as bulk_create, bulk_update, etc.

        The destination model is found by calling get_destination_model()

        The schema for the transformation is found in the oleeo_schema_registry and looked up using
        get_oleeo_schema_for_model.

        :param keys: The keys to pass to the values() method.
        :return: A list of dictionaries transformed to represent the destination model instances.
        """
        destination_model = self._get_destination_model()
        transform: Type[ModelSchema] = get_oleeo_schema_for_model(destination_model)

        include = self._parse_keys(destination_model, args) if args else None
        return (
            transform(**source_item).model_dump(include=include)
            for source_item in self.values()
        )

    def as_destination_values_list(self, *args, flat=False) -> Generator[Union[Tuple, Any], None, None]:
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
        :param flat: If True, return single values instead of 1-tuples.
        :return: A generator yielding tuples (or single values if flat=True) representing the destination model values.
        """
        # This attempts to adhere to the same interface as values_list() but may not be complete
        # where functionality is not required.
        destination_values = self.model.as_destination_values(*args)

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
        return (
            destination_model(**value) for value in destination_values
        )

    def as_destination_query(self, strict=True) -> QuerySet[models.Model]:
        """\
        :return: A queryset of destination model instances populated with data
        from this queryset.

        :param strict: If True, raise an error if the source and destination don't contain the same records.
        """
        destination_model = self._get_destination_model()
        pks = [*self.values_list("pk", flat=True)]

        destination_qs = destination_model.objects.filter(pk__in=pks)

        source_count = len(pks)
        destination_count = destination_qs.count()

        if strict and (source_count != destination_count):
            raise ValueError(f"{source_count} != {destination_count}, lists are not synchronized.")

        return destination_qs

    def pending_create(self) -> Self:
        """
        :return: List records that exist in this queryset but not in the destination model.
        """
        destination_model = self._get_destination_model()
        source_pks = set(self.values_list("pk", flat=True))
        destination_pks = set(destination_model.objects.values_list("pk", flat=True))

        new_pks = source_pks - destination_pks
        return self.filter(pk__in=new_pks)

    def pending_update(self) -> Self:
        """
        :return: List records that where the id matches but the update time differs from the destination model.
        """
        destination_model = self._get_destination_model()
        source_data = dict(self.values_list("pk", "row_last_updated"))
        destination_data = dict(
            destination_model.objects.values_list("pk", "last_updated")
        )

        common_pks = set(source_data.keys()) & set(destination_data.keys())

        pks_to_update = [
            source_pk for source_pk in common_pks
            if source_data[source_pk] != destination_data[source_pk]
        ]

        return self.filter(pk__in=pks_to_update)

    # There is no pending_delete as it would have to return records that exist in the
    # destination model but not in this queryset.

    def destination_pending_create(self, max_batch_size: Optional[int] = None) -> Generator[models.Model, None, None]:
        """
        :param max_batch_size: The maximum number of records to return.
        :return: Generator of Instances in the destination model matching this queryset that are pending creation.
        """
        pending: Self = self.pending_create()
        if max_batch_size:
            pending = pending[:max_batch_size]
        return pending.as_destination_instances()

    def destination_pending_update(self, max_batch_size: Optional[int] = None) -> QuerySet[models.Model]:
        """
        :return: Instances in the destination model matching this queryset that are pending an update.
        """
        pending: Self = self.pending_update()
        if max_batch_size:
            pending = pending[:max_batch_size]
        return pending.as_destination_query()

    def destination_pending_delete(self, max_batch_size: Optional[int] = None) -> QuerySet[models.Model]:
        """
        :return: Instances in the destination model matching this queryset that are pending an delete.
        """
        destination_model = self._get_destination_model()
        qs = self
        if max_batch_size:
            qs = qs[:max_batch_size]
        source_pks = [*qs.values_list("pk", flat=True)]
        destination_pending = destination_model.objects.exclude(pk__in=source_pks)
        return destination_pending

    def bulk_create_pending(self, max_batch_size: Optional[int] = None) -> List[models.Model]:
        """
        Bulk create records that exist in this queryset but not in the destination model.
        """
        destination_model = self._get_destination_model()
        destination_instances = self.destination_pending_create(max_batch_size=max_batch_size)

        return destination_model.objects.bulk_create(destination_instances,
                                                     batch_size=max_batch_size)

    def bulk_update_pending(self, max_batch_size: Optional[int] = None) -> List[models.Model]:
        """
        Bulk create records that exist in this queryset but not in the destination model.
        """
        destination_model = self._get_destination_model()
        destination_fields = [
            field.name for field in destination_model._meta.fields    # noqa
            if field.name != 'id'
        ]

        destination_instances = self.destination_pending_update(max_batch_size=max_batch_size)
        return destination_model.objects.bulk_update(destination_instances,
                                                     destination_fields,
                                                     batch_size=max_batch_size)

    def bulk_delete_pending(self) -> List[models.Model]:
        """
        bulk_delete_pending is not wanted since it's unsafe as FK relations aren't followed, .delete is sufficient.

        This is added mostly to stop a future dev adding it as it's missing.
        """
        raise NotImplementedError(
            "bulk_delete_pending is not implemented in JAO. "
            "Use bulk_mark_delete_pending() or delete_pending() instead."
        )

    # batch based bulk updates...

    def batch_mark_delete_pending(self, max_batch_size=10000, progress_bar=None):
        """
        Batch create pending records.

        This is intended for larger, non-list tables such as Vacancies.
        """
        dest_start = self.first().pk
        dest_end = self.last().pk

        if dest_end == self.last():
            return

        for batch_start, batch_end in sliding_window_range(dest_start, dest_end, max_batch_size, 0,
                                                           progress_bar=progress_bar):
            deleted = self.filter(pk__gte=batch_start, pk__lte=batch_end).mark_delete_pending(
                max_batch_size=max_batch_size)
            yield deleted

    def batch_bulk_update_pending(self, max_batch_size=10000, progress_bar=None):
        """
        Batch create pending records.

        This is intended for larger, non-list tables such as Vacancies.
        """
        dest_model = self.model.get_destination_model()
        dest_start = self.first().pk
        dest_end = self.last().pk

        if dest_end == self.last():
            return

        for batch_start, batch_end in sliding_window_range(dest_start, dest_end, max_batch_size, 0,
                                                           progress_bar=progress_bar):
            updated = self.filter(pk__gte=batch_start, pk__lte=batch_end) \
                .bulk_update_pending(max_batch_size=max_batch_size)
            yield updated

    def batch_bulk_create_pending(self, max_batch_size=10000, append=True, progress_bar=None):
        """
        Batch create pending records.

        This is intended for larger, non-list tables such as Vacancies.
        """

        if append:
            dest_model = self.model.get_destination_model()
            source_start = getattr(dest_model.objects.order_by("pk").last(), "pk", 0)
        else:
            source_start = 0

        source_end = self.last().pk

        if source_start == self.last():
            return

        # IDs are not contiguous query more from the source model than the max_batch_size
        extra = 50 + (max_batch_size // 10)
        for source_start, source_end in sliding_window_range(source_start, source_end, max_batch_size, extra,
                                                             progress_bar=progress_bar):
            created = self.filter(pk__gte=source_start, pk__lte=source_end) \
                .bulk_create_pending(max_batch_size=max_batch_size)
            yield created
    # End batch based bulk updates...

    def delete_pending(self, max_batch_size: Optional[int] = None) -> int:
        """
        Delete records that exist in the destination model but not in this queryset.
        """
        destination_instances = self.destination_pending_delete(max_batch_size=max_batch_size)
        return destination_instances.delete()

    def mark_delete_pending(self, max_batch_size: Optional[int] = None) -> int:
        """
        Mark models for deletion in the destination model.
        """
        destination_instances = self.destination_pending_delete(max_batch_size=max_batch_size)
        return destination_instances.update(is_deleted=True, last_updated=timezone.now())


class VacanciesQuerySet(UpstreamModelQuerySet):
    def exclude_known_bad(self):
        """
        Filter known bad records:

        salary_minimum:  Must be consist of digits and an optional decimal point
        salary_maximum_optional:  Can be null or digits and an optional decimal point

        Bad data found in the system:

        salary_minimum that is null.
        strings with commas
        arbitrary strings
        very large numbers.
        """
        return self.annotate(
            salary_minimum_is_valid=SqlServerIsValidDecimal('salary_minimum'),
            salary_maximum_optional_is_valid=SqlServerIsValidDecimalOrNull('salary_maximum_optional')
        ).filter(
            salary_minimum_is_valid=True,
            salary_maximum_optional_is_valid=True
        )
