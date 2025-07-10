import logging
from functools import lru_cache
from typing import Type

from plum import dispatch

from jao_backend.oleeo.models import ListAgeGroup
from jao_backend.oleeo.models import ListDisability
from jao_backend.oleeo.models import ListEthnicGroup
from jao_backend.oleeo.models import ListEthnicity
from jao_backend.oleeo.models import ListGender
from jao_backend.oleeo.models import ListJobGrade
from jao_backend.oleeo.models import ListReligion
from jao_backend.oleeo.models import ListSexualOrientation
from jao_backend.oleeo.models import ListTypeOfRole
from jao_backend.oleeo.models import Vacancies
from jao_backend.roles.models import OleeoGradeGroup
from jao_backend.roles.models import OleeoRoleTypeGroup
from jao_backend.vacancies.models import Vacancy

logger = logging.getLogger(__name__)

# Models to ingest these are in order.  Dependencies of other models should come first.
LIST_MODELS = [
    ListAgeGroup,
    # ListApplicantType,
    # ListApplicationStatus,
    # ListBusinessArea,
    # ListCityTown,
    # ListDepartment,
    ListDisability,
    ListEthnicGroup,
    ListEthnicity,
    ListGender,
    # ListLocationType,
    # ListPostcode,
    # ListProfession,
    # ListRegion,
    ListReligion,
    ListSexualOrientation,
    ListTypeOfRole,
    ListJobGrade,
    # ListVacancyApproach,
    # ListVacancyPostcode,
    # ListVacancyStatus,
]

DERIVED_MODELS = [
    OleeoGradeGroup,
    OleeoRoleTypeGroup,
]

VACANCY_MODELS = [Vacancies]

MODELS = [
    *LIST_MODELS,
    *DERIVED_MODELS,
    *VACANCY_MODELS,
]


def readable_pk_range(instances):
    """
    Return a readable string of the primary keys of the instances.
    """
    if not instances:
        return "[none]"

    if len(instances) == 1:
        return f"[{instances[0].pk}]"

    return f"[{instances[0].pk}-{instances[len(instances) - 1].pk}]"


class OleeoIngest:
    """
    Ingest OLEEO data stored in the R2D2 database.

    Prerequisites:

    INSTALLED_APPS must include "oleeo"
    """

    models = MODELS
    bulk_ingest = [(Vacancies, Vacancy)]
    """
    Model pairs listed here will use bulk ingest.
    """

    def __init__(self, max_batch_size=5000, progress_callback=None):
        self.max_batch_size = max_batch_size
        self.progress_callback = progress_callback

    def do_ingest(self, progress_bar=None):
        for source_model in self.models:
            self._ingest_model(source_model, progress_bar)

    def _ingest_model(self, source_model, progress_bar=None):
        destination_model = source_model.get_destination_model()
        in_bulk = (source_model, destination_model) in self.bulk_ingest
        logger.info(
            f"Ingesting {source_model.__name__} -> {destination_model.__name__}"
            + (" [bulk]" if in_bulk else "")
        )

        valid_objects = source_model.objects.valid_for_ingest()
        if in_bulk:
            for (
                source_instances,
                destination_instances,
            ) in valid_objects.bulk_create_pending(max_batch_size=self.max_batch_size):
                logger.info(
                    "Created %s/%s %s instances",
                    readable_pk_range(destination_instances),
                    readable_pk_range(source_instances),
                    destination_model.__name__,
                )
                self.after_ingest(
                    source_model,
                    destination_model,
                    source_instances,
                    destination_instances,
                )

            for (
                source_instances,
                destination_instances,
                count,
            ) in valid_objects.bulk_update_pending():
                logger.info(
                    "Updated %s/%s %s instances",
                    readable_pk_range(destination_instances),
                    readable_pk_range(source_instances),
                    destination_model.__name__,
                )
                self.after_ingest(
                    source_model,
                    destination_model,
                    source_instances,
                    destination_instances,
                )

            deleted, undeleted = valid_objects.update_deletion_marks()
        else:
            source_instances, destination_instances = (
                source_model.objects.valid_for_ingest().create_pending()
            )
            logger.info(
                "Created %s/%s %s instances",
                readable_pk_range(destination_instances),
                readable_pk_range(source_instances),
                destination_model.__name__,
            )
            self.after_ingest(
                source_model, destination_model, source_instances, destination_instances
            )

            source_instances, destination_instances, count = (
                source_model.objects.valid_for_ingest().update_pending()
            )
            logger.info(
                "Updated %s/%s %s instances",
                readable_pk_range(destination_instances),
                readable_pk_range(source_instances),
                destination_model.__name__,
            )
            self.after_ingest(
                source_model, destination_model, source_instances, destination_instances
            )

            deleted, undeleted = (
                source_model.objects.valid_for_ingest().update_deletion_marks()
            )

    @lru_cache(maxsize=1)
    def get_grade_groups(self):
        grade_groups = {
            grade_group.pk: set(grade_group.get_grades().values_list("pk", flat=True))
            for grade_group in OleeoGradeGroup.objects.all()
        }
        return grade_groups

    @lru_cache(maxsize=1)
    def get_role_types(self):
        role_types = {
            role_type.pk: set(role_type.get_role_types().values_list("pk", flat=True))
            for role_type in OleeoRoleTypeGroup.objects.all()
        }
        return role_types

    def update_vacancy_grades(self, source_instances=None, destination_instances=None):
        logger.info(
            "Updating vacancy grades for %d/%d",
            len(destination_instances),
            len(source_instances),
        )

        # in_bulk isn't used as source_instances may have been limited, preventing it's use.
        source_vacancies = {
            source_instance.pk: source_instance for source_instance in source_instances
        }

        # Cache vacancy grades - note: ingestion has enough records that it's possible
        # for new combinations to appear during ingestion.
        grade_groups = self.get_grade_groups()
        for destination_instance in destination_instances:
            source_instance = source_vacancies[destination_instance.pk]
            source_grades = grade_groups.get(source_instance.job_grade_id)
            if source_grades is None:
                logger.info("New job grade combination found, invalidating cache")
                self._ingest_model(ListJobGrade)
                self._ingest_model(OleeoGradeGroup)
                source_grades = self.get_grade_groups[source_instance.job_grade_id]

            destination_grades = {
                *destination_instance.vacancygrade_set.values_list("pk", flat=True)
            }
            if source_grades != destination_grades:
                destination_instance.grades.set(source_grades)

    def update_vacancy_role_types(
        self, source_instances=None, destination_instances=None
    ):
        logger.info(
            "Updating vacancy role types for %d/%d",
            len(destination_instances),
            len(source_instances),
        )

        # in_bulk isn't used as source_instances may have been limited, preventing it's use.
        source_vacancies = {
            source_instance.pk: source_instance for source_instance in source_instances
        }

        # Cache vacancy role type - note: ingestion has enough records that it's possible
        # for new combinations to appear during ingestion.
        role_types = self.get_role_types()
        for destination_instance in destination_instances:
            source_instance = source_vacancies[destination_instance.pk]
            source_role_types = role_types.get(source_instance.type_of_role_id)
            if source_role_types is None:
                logger.info("New role type combination found, invalidating cache")
                self._ingest_model(ListTypeOfRole)
                self._ingest_model(OleeoRoleTypeGroup)
                source_role_types = role_types[source_instance.type_of_role_id]

            destination_role_types = {
                *destination_instance.vacancyroletype_set.values_list("pk", flat=True)
            }
            if source_role_types != destination_role_types:
                destination_instance.role_types.set(source_role_types)

    @dispatch
    def after_ingest(
        self,
        source_model,
        destination_model,
        source_instances=None,
        destination_instances=None,
    ):
        """
        default dispatch (see plum dispatch docs https://beartype.github.io/plum/basic_usage.html)

        after_ingest is called after create and update.
        """
        pass

    @dispatch
    def after_ingest(
        self,
        source_model: Type[ListJobGrade],
        destination_model: Type[OleeoGradeGroup],
        source_instances=None,
        destination_instances=None,
    ):
        """
        Invalidate the cache of Grade combinations, after ingest.
        """
        self.get_grade_groups.cache_clear()

    @dispatch
    def after_ingest(
        self,
        source_model: Type[ListTypeOfRole],
        destination_model: Type[OleeoRoleTypeGroup],
        source_instances=None,
        destination_instances=None,
    ):
        """
        Invalidate the cache of Role Type combinations, after ingest.
        """
        self.get_role_types.cache_clear()

    @dispatch
    def after_ingest(
        self,
        source_model: Type[Vacancies],
        destination_model: Type[Vacancy],
        source_instances=None,
        destination_instances=None,
    ):
        """
        After creating or updating vacancies, build the foreign key relationships for vacancies.
        """
        if not destination_instances:
            logger.info(
                "No destination instances to update relationships for %s %s %s",
                destination_model.__name__,
                readable_pk_range(source_instances),
                readable_pk_range(destination_instances),
            )
            return

        logger.info(
            "Updating relationships for %s %s %s",
            destination_model.__name__,
            readable_pk_range(source_instances),
            readable_pk_range(destination_instances),
        )
        self.update_vacancy_grades(source_instances, destination_instances)
        self.update_vacancy_role_types(source_instances, destination_instances)
