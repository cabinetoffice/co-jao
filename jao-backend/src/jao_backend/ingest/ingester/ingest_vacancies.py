import logging

from django.conf import settings

from functools import lru_cache
from typing import Dict
from typing import Set
from typing import Type

from plum import Dispatcher

from jao_backend.ingest.ingester.helpers import readable_pk_range
from jao_backend.oleeo.sync_primitives import get_buckets_modulo
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
from jao_backend.roles.models import Grade
from jao_backend.roles.models import OleeoGradeGroup
from jao_backend.roles.models import RoleType
from jao_backend.roles.models import OleeoRoleTypeGroup
from jao_backend.vacancies.models import Vacancy

DEFAULT_BATCH_SIZE = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE

logger = logging.getLogger(__name__)


class OleeoVacanciesIngest:
    """
    Ingest OLEEO data stored in the R2D2 database.

    Prerequisites:

    INSTALLED_APPS must include "oleeo"
    """

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

    models = MODELS
    bulk_ingest = [
        (Vacancies, Vacancy),
    ]

    """
    Model pairs listed here will use bulk ingest.
    """

    dispatch = Dispatcher()

    def __init__(
        self,
        batch_size=DEFAULT_BATCH_SIZE,
        initial_vacancy_id=None,
        final_vacancy_id=None,
        progress_callback=None,
        create_only=False,
    ):
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.initial_vacancy_id = initial_vacancy_id
        self.create_only = create_only

    def do_ingest(self, progress_bar=None):
        for source_model in self.models:
            destination_model = source_model.get_destination_model()
            in_bulk = (source_model, destination_model) in self.bulk_ingest
            if in_bulk:
                initial_pk = None
                if destination_model == Vacancy:
                    initial_pk = self.initial_vacancy_id

                self._bulk_ingest_model(
                    source_model,
                    destination_model,
                    progress_bar,
                    initial_pk=initial_pk,
                    create_only=self.create_only,
                )
            else:
                self._ingest_model(
                    source_model,
                    destination_model,
                    progress_bar,
                    create_only=self.create_only,
                )

    def _bulk_ingest_model(
        self,
        source_model,
        destination_model,
        progress_bar=None,
        initial_pk=None,
        create_only=False,
    ):
        """
        Update models split into buckets by primary key.

        This is useful when there is a lot of data, such as with Vacancies.

        :param source_model: Upstream model to ingest from.
        :param destination_model: Destination model to ingest into.
        :param initial_pk: Primary key to start from, if None start from the first record.
        """

        buckets = [
            *get_buckets_modulo(
                source_model.objects_for_ingest, granularity_size=self.batch_size
            )
        ]
        for modulo_start, modulo_end, actual_min, actual_max in buckets:
            print(f"Processing modulo range {modulo_start}-{modulo_end}")
            print(f"Actual PKs: {actual_min} to {actual_max}")
            self._ingest_model(
                source_model,
                destination_model,
                pk_start=modulo_start, #hard code pk_start and pk_end for dev
                pk_end=modulo_end,
                progress_bar=progress_bar,
                create_only=create_only,
            )

    def _ingest_model(
        self,
        source_model,
        destination_model,
        pk_start=None,
        pk_end=None,
        progress_bar=None,
        create_only=False,
    ):
        """
        :param create_only:  Set to True only create new records; this is useful during deployment (especially during the initial deployment)
        """

        logger.info("Ingest: %s -> %s", source_model.__name__, destination_model.__name__)
        (source_instances, create_instances, update_instances, delete_qs) = (
            source_model.destination_pending_sync(
                pk_start=pk_start,
                pk_end=pk_end,
                include_update=not create_only,
                include_delete=not create_only,
            )
        )

        created_count = 0
        updated_count = 0

        if not any((create_instances, update_instances, delete_qs)):
            logger.info("No %s changed.", source_model)

        logger.info(
            "%s Create %s instances", source_model.__name__, len(create_instances)
        )
        if create_instances:
            created_count = destination_model.objects.bulk_create(
                create_instances,
            )
            self.after_ingest(
                source_model, destination_model, source_instances, create_instances
            )
        del create_instances

        logger.info(
            "%s Update %s instances", source_model.__name__, len(update_instances)
        )
        if update_instances:
            for instance in update_instances:
                instance.deleted = False

            non_pk_fields = [
                field.name
                for field in destination_model._meta.fields  # noqa
                if field.name not in ("id", "pk")
            ]
            updated_count = destination_model.objects.bulk_update(
                update_instances, non_pk_fields, batch_size=self.batch_size
            )
            self.after_ingest(
                source_model, destination_model, source_instances, update_instances
            )
        del update_instances

        deleted_count = 0
        if not create_only:
            deleted_count = delete_qs.update(is_deleted=False)

        return created_count, updated_count, deleted_count

    @staticmethod
    @lru_cache(maxsize=1)
    def get_grade_groups() -> Dict[int, Set[Grade]]:
        grade_groups = {
            grade_group.pk: set(grade_group.get_grades().values_list("pk", flat=True))
            for grade_group in OleeoGradeGroup.objects.all()
        }
        return grade_groups

    @staticmethod
    @lru_cache(maxsize=1)
    def get_role_types() -> Dict[int, Set[RoleType]]:
        role_types = {
            role_type.pk: set(role_type.get_role_types().values_list("pk", flat=True))
            for role_type in OleeoRoleTypeGroup.objects.all()
        }
        return role_types

    def update_vacancy_grades(self, source_instances=None, destination_instances=None):
        logger.info(
            "Updating vacancy grades for %d",
            len(destination_instances),
        )

        # in_bulk isn't used as source_instances may have been limited, preventing it's use.
        source_vacancies = {
            source_instance.pk: source_instance for source_instance in source_instances
        }

        del source_instances

        # Cache vacancy grades - note: ingestion has enough records that it's possible
        # for new combinations to appear during ingestion.
        grade_groups = self.get_grade_groups()
        for destination_instance in destination_instances:
            source_instance = source_vacancies[destination_instance.pk]
            source_grades = grade_groups.get(source_instance.job_grade_id)
            if source_grades is None:
                logger.info("New job grade combination found, invalidating cache")
                self._ingest_model(ListJobGrade, ListJobGrade.get_destination_model())
                self._ingest_model(
                    OleeoGradeGroup, OleeoGradeGroup.get_destination_model()
                )
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
            "Updating vacancy role types for %d",
            len(destination_instances),
        )

        # in_bulk isn't used as source_instances may have been limited, preventing it's use.
        source_vacancies = {
            source_instance.pk: source_instance for source_instance in source_instances
        }

        del source_instances

        # Cache vacancy role type - note: ingestion has enough records that it's possible
        # for new combinations to appear during ingestion.
        role_types = self.get_role_types()
        for destination_instance in destination_instances:
            source_instance = source_vacancies[destination_instance.pk]
            source_role_types = role_types.get(source_instance.type_of_role_id)
            if source_role_types is None:
                logger.info("New role type combination found, invalidating cache")
                self._ingest_model(
                    ListTypeOfRole, ListTypeOfRole.get_destination_model()
                )
                self._ingest_model(
                    OleeoRoleTypeGroup, OleeoRoleTypeGroup.get_destination_model()
                )
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
                "No destination instances to update relationships for %s %s",
                destination_model.__name__,
                readable_pk_range(destination_instances),
            )
            return

        logger.info(
            "Updating relationships for %s %s",
            destination_model.__name__,
            readable_pk_range(destination_instances),
        )
        self.update_vacancy_grades(source_instances, destination_instances)
        self.update_vacancy_role_types(source_instances, destination_instances)
