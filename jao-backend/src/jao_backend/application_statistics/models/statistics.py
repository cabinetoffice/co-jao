from django.db import models

from jao_backend.application_statistics.models import AgeGroup
from jao_backend.application_statistics.models import Disability
from jao_backend.application_statistics.models import EthnicGroup
from jao_backend.application_statistics.models import Ethnicity
from jao_backend.application_statistics.models import Gender
from jao_backend.roles.models import Grade
from jao_backend.roles.models import RoleType
from jao_backend.vacancies.models import Vacancy


class ApplicationStatistic(models.Model):
    """
    Abstract base class for all aggregated application statistics.
    """

    vacancy = models.OneToOneField(
        Vacancy,
        on_delete=models.CASCADE,
        unique=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField(default=False)
    """
    We mark deletion; we are downstream of OLEEO and may need deletion to be separate from the point
    when synchronisation with OLEEO occurs.
    """

    class Meta:
        abstract = True


class ProtectedCharacteristicStatistic(ApplicationStatistic):
    """Abstract base class for all protected characteristic mixins"""

    # Using a class like this makes it possible to iterate through only
    # the protected characteristic mixins when needed.
    class Meta:
        abstract = True


class AgeGroupStatistic(ProtectedCharacteristicStatistic):
    """
    Aggregated age groups of applicants for a vacancy.
    """

    age_group = models.ForeignKey(
        AgeGroup,
        on_delete=models.CASCADE,
        related_name="age_group_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "age_group"],
                name="unique_vacancy_age_group",
            )
        ]


class DisabilityStatistic(ProtectedCharacteristicStatistic):
    """Aggregated disability statistics for applicants to a vacancy."""

    disability = models.ForeignKey(
        Disability,
        on_delete=models.CASCADE,
        related_name="disability_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "disability"],
                name="unique_vacancy_disability",
            )
        ]


class EthnicityStatistic(ProtectedCharacteristicStatistic):
    """Aggregated ethnicity statistics for applicants to a vacancy."""

    ethnicity = models.ForeignKey(
        Ethnicity,
        on_delete=models.CASCADE,
        related_name="ethnicity_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "ethnicity"],
                name="unique_vacancy_ethnicity",
            )
        ]


class EthnicGroupStatistic(ProtectedCharacteristicStatistic):
    """Aggregated ethnic group statistics for applicants to a vacancy."""

    ethnic_group = models.ForeignKey(
        EthnicGroup,
        on_delete=models.CASCADE,
        related_name="ethnic_group_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "ethnic_group"],
                name="unique_vacancy_ethnic_group",
            )
        ]


class GenderStatistic(ProtectedCharacteristicStatistic):
    """Aggregated gender statistics for applicants to a vacancy."""

    gender = models.ForeignKey(
        Gender,
        on_delete=models.CASCADE,
        related_name="gender_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "gender"],
                name="unique_vacancy_gender",
            )
        ]


class JobGradeStatistic(ProtectedCharacteristicStatistic):
    """Aggregated job grade statistics for applicants to a vacancy."""

    job_grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="job_grade_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "job_grade"],
                name="unique_vacancy_job_grade",
            )
        ]


class RoleTypeStatistic(ProtectedCharacteristicStatistic):
    """Aggregated role type statistics for applicants to a vacancy."""

    role_type = models.ForeignKey(
        RoleType,
        on_delete=models.CASCADE,
        related_name="role_type_statistics",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "role_type"],
                name="unique_vacancy_role_type",
            )
        ]
