"""
Oleeo / R2D2 specific querysets for syncing vacancies.
"""

from typing import Self

from django.db.models import F

from jao_backend.common.db.functions import IsValidDecimal
from jao_backend.common.db.functions import IsValidDecimalOrNull
from jao_backend.oleeo.base_querysets import UpstreamModelQuerySet


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
