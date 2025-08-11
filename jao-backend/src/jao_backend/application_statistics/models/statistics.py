from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_percentagefield.db.models import PercentageField
from polymorphic.models import PolymorphicModel

from jao_backend.vacancies.models import Vacancy


class BaseVacancyStatistic(PolymorphicModel):
    """
    Note:  subclasses should setup constraints using vacancy as one of the fields.
    """

    vacancy = models.OneToOneField(
        Vacancy,
        on_delete=models.CASCADE,
        null=True,
    )

    updated_at = models.DateTimeField()

    class Meta:
        abstract = True


class BaseApplicationCategoryStatistic(BaseVacancyStatistic):
    """
    Information applying to a whole category of applicants.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class VacancyStatistic(BaseVacancyStatistic):
    """
    Information about a single vacancy.
    """

    total_applications = models.PositiveIntegerField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy"],
                name="vacancy_statistic_unique_vacancy",
            )
        ]


class AggregatedApplicationStatistic(BaseApplicationCategoryStatistic):
    object_id = models.PositiveIntegerField(db_index=True)
    """
    object_id matches the pk on the ListModel
    """
    content_object = GenericForeignKey("content_type", "object_id")
    percent_applications = PercentageField()
    """
    How many applications this category represents as a percentage of the applicants who
    answered the question.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "content_type", "object_id"],
                name="aggregated_application_unique_vacancy_total_applications",
            )
        ]
