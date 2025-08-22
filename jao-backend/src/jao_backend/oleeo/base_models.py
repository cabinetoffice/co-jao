from contextlib import suppress
from functools import lru_cache
from typing import Type
from typing import Union

from django.apps import apps
from django.db import models

from jao_backend.common.db.models.models import ListModel
from jao_backend.oleeo.errors import NoDestinationModel
from jao_backend.oleeo.querysets import UpstreamModelQuerySet


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

    objects = UpstreamModelQuerySet.as_manager()

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


class OleeoUpstreamModel(models.Model, UpstreamModelMixin):

    ingest_last_updated_field = "row_last_updated"

    objects = UpstreamModelQuerySet.as_manager()

    class Meta:
        abstract = True
