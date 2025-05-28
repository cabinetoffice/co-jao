from django.db import models

#from django_percentagefield.db.models import PercentageField

from jao_backend.application_statistics.models import AgeGroup
from jao_backend.application_statistics.models import Disability
from jao_backend.application_statistics.models import Gender
from jao_backend.application_statistics.models import Ethnicity
from jao_backend.application_statistics.models import EthnicGroup
from jao_backend.roles.models import Grade
from jao_backend.roles.models import RoleType

from jao_backend.vacancies.models import Vacancy


# class ProtectedCharacteristic(models.Model):
#     """Abstract base class for all protected characteristic mixins"""
#
#     class Meta:
#         abstract = True
#
#
# class ApplicationStatus(models.Model):
#     """Abstract base class for application status tracking"""
#
#     failed_sift_1 = PercentageField()
#     failed_sift_2 = PercentageField()
#     passed_sift = PercentageField()
#     failed_interview = PercentageField()
#     offer = PercentageField()
#     reserve = PercentageField()
#     total_applications = models.IntegerField(default=0., null=True)
#     average_applicant_score = PercentageField()
#
#     # TODO - verify what needs to be aggregated here, combined failed_sift could be an annotation if needed?
#     # @property
#     # def percent_passed_sift(self):
#     #     if not self.total_applications:
#     #         return 0
#     #     return (
#     #         (self.passed_sift / self.total_applications) * 100
#     #         if self.passed_sift is not None
#     #         else 0
#     #     )
#     #
#     # @property
#     # def percent_failed_sift(self):
#     #     if not self.total_applications:
#     #         return 0
#     #     failed_sift_1 = self.failed_sift_1 or 0
#     #     failed_sift_2 = self.failed_sift_2 or 0
#     #     return ((failed_sift_1 + failed_sift_2) / self.total_applications) * 100
#
#     class Meta:
#         abstract = True
#
#
# class AgeGroup(ProtectedCharacteristic):
#     """Age group mixin for application statistics"""
#
#     age_group_16_24 = PercentageField()
#     age_group_25_29 = models.DecimalField(
#         default=0., null=True, decimal_places=2, max_digits=4
#     )  # Note: Corrected from 25_20
#     age_group_30_34 = PercentageField()
#     age_group_35_39 = PercentageField()
#     age_group_40_44 = PercentageField()
#     age_group_45_49 = PercentageField()
#     age_group_50_54 = PercentageField()
#     age_group_55_59 = PercentageField()
#     age_group_60_64 = PercentageField()
#     age_group_65_plus = PercentageField()
#     age_group_prefer_not_to_disclose = PercentageField()
#     age_group_restricted_data = PercentageField()
#
#     class Meta:
#         abstract = True
#
#
# class Disability(ProtectedCharacteristic):
#     """Disability mixin for application statistics"""
#
#     disability_disabled = models.DecimalField(
#         default=0., null=True, decimal_places=2, max_digits=4
#     )
#     disability_non_disabled = PercentageField()
#     disability_prefer_not_to_say = PercentageField()
#     disability_restricted_data = PercentageField()
#
#     class Meta:
#         abstract = True
#
#
# class Gender(ProtectedCharacteristic):
#     """Gender mixin for application statistics"""
#
#     gender_female = PercentageField()
#     gender_male = PercentageField()
#     gender_other = PercentageField()
#     gender_prefer_not_to_say = PercentageField()
#     gender_restricted_data = PercentageField()
#
#     class Meta:
#         abstract = True
#
#
# class EthnicGroup(ProtectedCharacteristic):
#     """Ethnic group mixin for application statistics"""
#
#     ethnic_group_asian_asian_british = PercentageField()
#     ethnic_group_black_african_caribbean_black_british = models.DecimalField(
#         default=0., null=True, decimal_places=2, max_digits=4
#     )
#     ethnic_group_mixed_multiple_ethnic_groups = PercentageField()
#     ethnic_group_other = PercentageField()
#     ethnic_group_prefer_not_to_disclose = PercentageField()
#     ethnic_group_restricted_data = PercentageField()
#     ethnic_group_white = PercentageField()
#
#     class Meta:
#         abstract = True
#
#
# class ApproachName(ProtectedCharacteristic):
#     """Approach name mixin for application statistics"""
#
#     approach_name_50 = PercentageField()
#     approach_name_across_government = models.DecimalField(
#         default=0., null=True, decimal_places=2, max_digits=4
#     )  # Note: Corrected from gorvernment
#     approach_name_external = PercentageField()
#     approach_name_internal = PercentageField()
#     approach_name_pre_release = PercentageField()
#
#     class Meta:
#         abstract = True
#
#
# class ApplicationStatistic(
#     AgeGroup,
#     Disability,
#     Gender,
#     EthnicGroup,
#     ApproachName,
#     ApplicationStatus,
# ):
#     """
#     Main model that combines all protected characteristic mixins and application status
#     to track application statistics for vacancies
#     """
#
#     vacancy = models.OneToOneField(
#         Vacancy,
#         on_delete=models.CASCADE,
#         related_name="application_statistics",
#         unique=True,
#         null=True,
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f"Statistics for {self.vacancy}"
#

class ApplicationStatistic(models.Model):
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
