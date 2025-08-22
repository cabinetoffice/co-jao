from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from polymorphic.models import PolymorphicModel

from jao_backend.oleeo.models import ListDisability
from jao_backend.vacancies.models import Vacancy


class BaseVacancyStatistic(PolymorphicModel):
    """
    Note:  subclasses should setup constraints using vacancy as one of the fields.
    """

    vacancy = models.ForeignKey(
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
    """content_type corresponding the protected characteristic model, 
       e.g. AgaGroup, Disability.
    """

    class Meta:
        abstract = True


class VacancyStatistic(BaseVacancyStatistic):
    """
    Any fields adding data to the vacancy.
    """

    total_applications = models.PositiveIntegerField(null=True)
    """Count of all applications."""

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
    object_id matches the pk on the list model,
    
    see `content_type` for the model type - in this model `content_object` can be used
    to access the actual data. 
    """

    content_object = GenericForeignKey("content_type", "object_id")
    ratio = models.DecimalField(decimal_places=4, max_digits=6)
    """
    How many applications this category represents of the applicants who
    answered the question, normalised to a ratio from 0.0 to 1.0
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "content_type", "object_id"],
                name="aggregated_application_unique_vacancy_total_applications",
            )
        ]

    def __repr__(self):
        return (
            f"<AggregatedApplicationStatistic "
            f"vacancy_id={self.vacancy_id}, "
            f"content_object={repr(self.content_object)}, "
            f"ratio={self.ratio}>"
        )
