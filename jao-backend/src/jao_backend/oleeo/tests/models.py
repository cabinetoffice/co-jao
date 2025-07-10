"""
These models should only be added during testing.
"""

from django.db import models

from jao_backend.oleeo.models import OleeoUpstreamModel
from jao_backend.oleeo.querysets import VacanciesQuerySet


class TestListAgeGroup(OleeoUpstreamModel):
    """
    This is based on the OLEEO ListAgeGroup model,

    Each row contains a single age group.
    """

    age_group_id = models.AutoField(primary_key=True)
    age_group_desc = models.TextField()
    row_last_updated = models.DateTimeField()

    destination_model = "application_statistics.AgeGroup"

    class Meta:
        """
        Unlike the actual ListAgeGroup model this is managed,
        and in the default database.

        This allows the use of factories.
        """

        managed = True


class TestVacancies(OleeoUpstreamModel):
    """Test model for testing VacanciesQuerySet functionality.

    This is a minimal model, field names are copied from the OLEEO Vacancies model.

    Each row contains a single vacancy.
    """

    destination_model = "vacancies.Vacancy"

    vacancy_id = models.IntegerField(primary_key=True)
    vacancy_title = models.TextField()
    salary_minimum = models.TextField(blank=True, null=True)
    salary_maximum_optional = models.TextField(blank=True, null=True)

    objects = VacanciesQuerySet.as_manager()

    class Meta:
        """
        Unlike the actual Vacancies model this is managed,
        and in the default database.

        This allows the use of factories.
        """

        managed = True


class TestVacanciesTimestamps(OleeoUpstreamModel):
    vacancy = models.ForeignKey(
        primary_key=True,
        to=TestVacancies,
        on_delete=models.CASCADE,
        related_name="vacanciestimestamps",
    )
    live_date = models.DateTimeField()
    closing_date = models.DateTimeField()

    class Meta:
        """
        Unlike the actual Vacancies model this is managed,
        and in the default database.

        This allows the use of factories.
        """

        managed = True
