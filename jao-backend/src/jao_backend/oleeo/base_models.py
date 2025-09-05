from functools import cache
from functools import lru_cache
from typing import Type
from typing import Union

from django.apps import apps
from django.db import models
from djantic import ModelSchema

from jao_backend.ingest.ingester.schema_registry import get_model_transform_schema
from jao_backend.oleeo.base_querysets import UpstreamModelQuerySet
from jao_backend.oleeo.errors import DestinationModelNotFound
from jao_backend.oleeo.errors import NoDestinationModel
from jao_backend.oleeo.sync_primitives import destination_pending_create_update_delete


class UpstreamModelMixin:
    """
    Base class for List views on OLEEO/R2D2 List* that are reflected on JAO.

    Implementing classes should define destination_model with app_name.model_name,
    e.g. "application_statistics.AgeGroups".

    Example:

    ... class SomeList(ListModelBase):
    ...    destination_model = "application_statistics.AgeGroups"
    >>> SomeList.get_destination_model()
    <class 'jao_backend.application_statistics.models.AgeGroups'>

    Note: this is not a module import path and using one will fail, the format is the one
    used in django migrations as used by apps.get_model.

    This will fail: "jao_backend.application_statistics.models.AgeGroups"

    Data can be extracted from the source model, transformed using a pydantic schema from
    oleeo_schema_registry, and then saved to the destination model.

    Models that extend ListModelBase have a default manager that returns ListModelQuerySet
    which enables bulk synchronization from OLEEO/R2D2 to JAO.

    See: bulk_create_pending(), bulk_update_pending() and bulk_delete_pending() in ListModelQuerySet.
    """

    destination_model: Union[str, Type[models.Model]] = None
    ingest_last_updated_field = None
    ingest_unique_id_field = "pk"
    """
    During ingest the field named here will be used to match records from upstream and downstream models.
    
    The upstream field and equivalent downstream field must both be unique. 
    """

    # Note, the name 'objects' is not used, in abstract model classes it is defaulted back to the default
    # Manager, so use `objects_for_ingest` instead.
    objects_for_ingest = models.Manager.from_queryset(UpstreamModelQuerySet)()

    @classmethod
    def get_ingest_unique_id_field(cls):
        if cls.ingest_unique_id_field == "pk":
            return cls._meta.pk.name  # noqa

        return cls.ingest_unique_id_field

    @classmethod
    def get_ingest_last_updated_field(cls):
        """
        :return: name of the field used to store the last updated time.

        This field is used as an initial filter to find upstream data for ingest.
        """
        if cls.ingest_last_updated_field:
            return cls.ingest_last_updated_field

        return ValueError(f"last updated field is not set on {cls.__name__}.")

    @classmethod
    @lru_cache(maxsize=1)
    def get_destination_model(cls):
        """
        Returns the destination model specified in the destination_model attribute.

        :return: The model class specified in destination_model attribute.
        """
        model_path = cls.destination_model
        if isinstance(model_path, models.Model):
            return model_path

        if model_path is None:
            raise NoDestinationModel(
                f"{cls.__name__}.destination_model must have a destination_model set in"
                " the format: app_name.model_name"
            )

        # Parse the string into app_label and model_name using rsplit
        app_label, model_name = model_path.rsplit(".", 1)  # Not comma, but period

        # Get the model class
        try:
            model_class = apps.get_model(app_label=app_label, model_name=model_name)
        except LookupError:
            raise DestinationModelNotFound(
                f"{cls.__name__}.destination_model '{model_path}' does not exist. "
            )
        return model_class

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

    def as_destination_dict(self):
        """
        :return: A dict of the data in this model, transformed to match the destination model.

        This is suitable to pass to create or update methods of the destination model.
        """
        destination_model = self.get_destination_model()
        transform: Type[ModelSchema] = get_model_transform_schema(destination_model)

        # Use Djantic (Pydantic) to transform data from this model to the destination model.
        # aliases denote names on the source side, names on the destination.
        kwargs = {
            value.alias if value.alias else name: getattr(
                self, value.alias if value.alias else name
            )
            for name, value in transform.model_fields.items()
        }

        result_kwargs = transform(**kwargs).model_dump()
        return result_kwargs

    @classmethod
    @cache
    def get_id_fields(cls):
        """
        :return : A tuple of the source and destination unique id fields.

        These id fields are used to match source and destination records.
        """
        id_field = cls.get_ingest_unique_id_field()
        dest_id_field = cls.get_destination_field_or_alias(id_field)
        return id_field, dest_id_field

    @classmethod
    def get_destination_field_or_alias(cls, name):
        """
        :return: field from destination that matches the source ingest field.

        This is only used when a single field is needed, in most cases it's
        better to directly use the transform, which makes it easy to do more
        than one operation at a time (e.g. renames / mapping).
        """
        destination_model = cls.get_destination_model()
        transform = get_model_transform_schema(destination_model)

        # Django supports a generic "pk" field, which needs resolving before
        # passing to pydantic.
        if name == "pk":
            name = cls._meta.pk.name  # noqa

        if name in transform.model_fields:
            return name

        for field_name, field_info in transform.model_fields.items():
            if field_info.alias == name:
                return field_name

        raise ValueError(f"Field '{name}' not found in transform model fields.")

    def destination_requires_update(self, destination_instance):
        update_field = self.get_ingest_last_updated_field()
        destination_update_field = self.get_destination_field_or_alias(update_field)

        assert self.pk == destination_instance.pk, "Mismatched instances"  # noqa

        return getattr(self, update_field) != getattr(
            destination_instance, destination_update_field
        )

    @classmethod
    def destination_pending_sync(
        cls,
        pk_start=None,
        pk_end=None,
        include_create=True,
        include_update=True,
        include_delete=True,
    ):
        """
        :param pk_start: If the primary key field supports numeric lookups, only consider instances with pk >= pk_start
        :param pk_end: If the primary key field supports numeric lookups, only consider instances with pk <= pk_end
        :param include_create: Include source-only instances (source_instance, None)
        :param include_update: Include changed matching instances (source_instance, dest_instance)
        :param include_delete: Include dest-only instances (None, dest_instance)

        :return: source_qs: QuerySet, [new_source_instances...], [update_source_instances], delete_qs: QuerySet


        Given a source and destination model that are comparable return:
        - source_qs: The source queryset, limited according to pk_start and pk_end and .valid_for_ingest())
        - a list of new instances to create in the destination
        - a list of existing instances to update in the destination
        - a queryset of instances to mark as deleted in the destination
        """
        destination_model = cls.get_destination_model()
        return destination_pending_create_update_delete(
            cls,
            destination_model,
            pk_start,
            pk_end,
            include_create=include_create,
            include_changed=include_update,
            include_delete=include_delete,
        )


class OleeoUpstreamModel(models.Model, UpstreamModelMixin):
    objects_for_ingest = models.Manager.from_queryset(UpstreamModelQuerySet)()

    ingest_last_updated_field = "row_last_updated"

    class Meta:
        abstract = True
