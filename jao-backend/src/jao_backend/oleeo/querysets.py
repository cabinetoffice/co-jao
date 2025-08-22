"""
Oleeo / R2D2 specific querysets for syncing vacancies.
"""

from contextlib import suppress
from typing import Self, Type
from typing import Union

from django.db.models import Count
from django.db.models import F
from django.db.models import Model
from django.db.models import Window
from django.db.models.functions import Cast
from django.forms import DecimalField

from jao_backend.common.db.models.models import ListModel
from jao_backend.common.db.functions import IsValidDecimal
from jao_backend.common.db.functions import IsValidDecimalOrNull
from jao_backend.oleeo.apps import OleeoConfig
from jao_backend.oleeo.errors import NoDestinationModel

# from jao_backend.oleeo.base_models import UpstreamModelMixin
from jao_backend.oleeo.base_querysets import UpstreamModelQuerySet

from django.apps import apps

app_config = apps.get_app_config("oleeo")


def is_list_model(model: Union[Model, "UpstreamModelMixin"]) -> bool:
    # destination_model = None is set on Upstream Models that haven't been configured, calling get_destination_model
    # on these would raise NoDestinationModel, so ignore it here.
    with suppress(NoDestinationModel):
        return issubclass(model.get_destination_model(), ListModel)
    return False


def get_related_list_models(model: Type[Model]) -> dict[str, Model]:
    """
    :param model: Upstream model for ingest.
    :return: dict of {name: model} of any models that extend ListModel
    """
    return {
        field.name: field.related_model
        for field in model._meta.fields  # noqa
        if getattr(field, "related_model", False) and is_list_model(field.related_model)
    }


class VacanciesQuerySet(UpstreamModelQuerySet):

    def annotate_salary_range_is_valid(self) -> Self:
        """
        Annotate the queryset with salary range validation.
        """
        return self.annotate(
            salary_minimum_is_valid=IsValidDecimal("salary_minimum"),
            salary_maximum_optional_is_valid=IsValidDecimalOrNull(
                "salary_maximum_optional"
            ),
        )

    def annotate_dates(self):
        return (
            self.select_related("vacanciestimestamps")
            .filter(vacanciestimestamps__isnull=False)
            .annotate(
                live_date=F("vacanciestimestamps__live_date"),
                closing_date=F("vacanciestimestamps__closing_date"),
            )
        )

    def valid_timestamps(self):
        """
        - Upstream can only have one VacanciesTimestamp per Vacancies because the fk is also a primary key.
        - Filter down to records that have a live_date and closing_date.
        """
        return self.annotate_dates().filter(
            live_date__isnull=False, closing_date__isnull=False
        )

    def valid_salary_ranges(self) -> Self:
        return self.annotate_salary_range_is_valid().filter(
            salary_minimum_is_valid=True, salary_maximum_optional_is_valid=True
        )

    def valid_for_ingest(self):
        """
        :return records that are valid for ingestion:

        Removes known bad records:

        - salary_minimum: string of digits, compatible with decimal.Decimal
        - salary_maximum_optional:  None or string of digits, compatible with decimal.Decimal

        Bad data found in the system:

        - salary_minimum that is null.
        - strings with commas
        - arbitrary strings
        - very large numbers.
        """
        return self.valid_salary_ranges().valid_timestamps().annotate_dates()
