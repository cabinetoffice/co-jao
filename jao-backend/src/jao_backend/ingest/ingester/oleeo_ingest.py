import logging

from django.db import transaction
from django.conf import settings

from jao_backend.oleeo.models import ListAgeGroup
from jao_backend.oleeo.models import ListApplicantType
from jao_backend.oleeo.models import ListApplicationStatus
from jao_backend.oleeo.models import ListBusinessArea
from jao_backend.oleeo.models import ListCityTown
from jao_backend.oleeo.models import ListDepartment
from jao_backend.oleeo.models import ListDisability
from jao_backend.oleeo.models import ListEthnicGroup
from jao_backend.oleeo.models import ListEthnicity
from jao_backend.oleeo.models import ListGender
from jao_backend.oleeo.models import ListJobGrade
from jao_backend.oleeo.models import ListLocationType
from jao_backend.oleeo.models import ListPostcode
from jao_backend.oleeo.models import ListProfession
from jao_backend.oleeo.models import ListRegion
from jao_backend.oleeo.models import ListReligion
from jao_backend.oleeo.models import ListSexualOrientation
from jao_backend.oleeo.models import ListTypeOfRole
from jao_backend.oleeo.models import ListVacancyApproach
from jao_backend.oleeo.models import ListVacancyPostcode
from jao_backend.oleeo.models import ListVacancyStatus
from jao_backend.oleeo.models import Vacancies

logger = logging.getLogger(__name__)

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
    ListJobGrade,
    # ListLocationType,
    # ListPostcode,
    # ListProfession,
    # ListRegion,
    ListReligion,
    ListSexualOrientation,
    ListTypeOfRole,
    # ListVacancyApproach,
    # ListVacancyPostcode,
    # ListVacancyStatus,
]

DATA_MODELS = [
    Vacancies,
]


class OleeoIngest:
    """
    Ingest OLEEO data stored in the R2D2 database.

    Prerequisites:

    INSTALLED_APPS must include "oleeo"
    """

    @transaction.atomic
    def synchronise_lists(self):
        for list_model in LIST_MODELS:
            created = list_model.objects.create_pending()
            updated = list_model.objects.update_pending()
            deleted = list_model.objects.mark_delete_pending()
            yield list_model, (created, updated, deleted)

    @transaction.atomic
    def synchronise_large_models(self):
        for data_model in DATA_MODELS:
            qs = data_model.objects.exclude_known_bad()
            total_created = 0
            for created in qs.bulk_create_pending():
                total_created += len(created)

            for total_updated in qs.bulk_update_pending():
                pass

            qs.mark_delete_pending()

            yield data_model, (total_created, total_updated)

    @transaction.atomic
    def synchronise_aggregated_statistics(self):
        """
        Synchronise the statistics models with the OLEEO data.
        """
        # TODO:  Aggregation queries are currently too slow so this is not implemented yet.
        logging.info("Synchronising aggregated statistics is not implemented yet.")

    @transaction.atomic
    def update(self):
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            raise ValueError("OLEEO ingest is not enabled")

        for model, (created, updated, deleted) in self.synchronise_lists():
            logging.info("synced %s", model.__name__)

        for model, (created, updated) in self.synchronise_large_models():
            logging.info("synced %s", model.__name__)

        self.synchronise_aggregated_statistics()
