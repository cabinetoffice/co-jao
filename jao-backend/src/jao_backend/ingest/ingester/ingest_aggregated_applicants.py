from django.conf import settings
from django.db import transaction
from django.utils.log import logging
from django.db.models import Count, F, DecimalField, Max, Q
from django.db.models.functions import Cast
from django.contrib.contenttypes.models import ContentType
from contextlib import suppress
from django.db.models import Model

from jao_backend.vacancies.models import Vacancy
from jao_backend.common.models import ListModel
from jao_backend.application_statistics.models import AggregatedApplicationStatistic
from jao_backend.oleeo.models import Dandi, Vacancies
from jao_backend.oleeo.base_models import NoDestinationModel
from jao_backend.oleeo.base_querysets import sliding_window_range

logger = logging.getLogger(__name__)


def is_list_model(model: Model):
    with suppress(NoDestinationModel):
        return issubclass(model.get_destination_model(), ListModel)
    return False


def get_related_list_models(model: Model):
    return {
        field.name: field.related_model
        for field in model._meta.fields
        if getattr(field, "related_model", False) and is_list_model(field.related_model)
    }


class OleeoApplicantStatisticsAggregator:
    def __init__(self, batch_size, initial_vacancy_id):
        self.batch_size = batch_size
        self.initial_vacancy_id = initial_vacancy_id

    def _get_vacancy_statistics_per_characteristic(
        self, vacancy_id_start, vacancy_id_end, characteristic_field
    ):
        from django.db.models import Subquery, OuterRef

        field_path = f"applications__dandi__{characteristic_field}"
        total_apps_subquery = (
            Vacancies.objects.valid_for_ingest()
            .filter(
                vacancy_id=OuterRef("vacancy_id"),
                applications__isnull=False,
                applications__dandi__isnull=False,
            )
            .annotate(total_count=Count("applications", distinct=True))
            .values("total_count")
        )

        return (
            Vacancies.objects.valid_for_ingest()
            .filter(
                applications__isnull=False,
                applications__dandi__isnull=False,
                vacancy_id__gte=vacancy_id_start,
                vacancy_id__lte=vacancy_id_end,
                **{f"{field_path}__isnull": False},
            )
            .values("vacancy_id", field_path)
            .annotate(
                characteristic_count=Count("applications"),
                total_applications=Subquery(total_apps_subquery),
                ratio=Cast(
                    F("characteristic_count") * 1.0 / F("total_applications"),
                    DecimalField(max_digits=15, decimal_places=14),
                ),
                latest_updated=Max("applications__dandi__row_last_updated"),
                object_id=F(field_path),
            )
            .order_by("vacancy_id", field_path)
        )

    def _create_statistics_from_characteristic_data(
        self, characteristic_data, characteristic_field, relations
    ):
        src_list_model = relations[characteristic_field]
        destination_list_model = src_list_model.get_destination_model()
        content_type = ContentType.objects.get_for_model(destination_list_model)

        for row in characteristic_data:
            yield AggregatedApplicationStatistic(
                vacancy_id=row["vacancy_id"],
                content_type=content_type,
                object_id=row["object_id"],
                ratio=row["ratio"],
                updated_at=row["latest_updated"],
            )

    def do_ingest(self):
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled")
            raise ValueError("OLEEO integration is not enabled")

        max_batch_size = (
            self.batch_size or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
        )
        relations = get_related_list_models(Dandi)
        max_vacancy_id = Vacancy.objects.order_by("pk").last().pk

        logger.info("Aggregate.. %s", max_vacancy_id)
        logger.info("Relations found: %s", list(relations.keys()))
        logger.info("Update aggregated statistics")

        initial_vacancy_id = (
            Vacancy.objects.first().pk
            if self.initial_vacancy_id is None
            else self.initial_vacancy_id
        )
        max_id = Vacancy.objects.last().pk

        for batch_start, batch_end in sliding_window_range(
            initial_vacancy_id, max_id, max_batch_size, 0, progress_bar=None
        ):
            logger.info(f"Processing batch {batch_start}-{batch_end}")
            with transaction.atomic():
                deleted_count = AggregatedApplicationStatistic.objects.filter(
                    vacancy_id__gte=batch_start, vacancy_id__lte=batch_end
                ).delete()[0]
                logger.info(f"  Deleted {deleted_count} existing statistics")

                statistics = []
                for characteristic_field in relations.keys():
                    logger.info(f"  Processing {characteristic_field}...")
                    characteristic_data = (
                        self._get_vacancy_statistics_per_characteristic(
                            batch_start, batch_end, characteristic_field
                        )
                    )
                    statistics.extend(
                        list(
                            self._create_statistics_from_characteristic_data(
                                characteristic_data, characteristic_field, relations
                            )
                        )
                    )

                if statistics:
                    count = AggregatedApplicationStatistic.objects.bulk_create(
                        statistics
                    )
                    logger.info(
                        f"  Batch {batch_start}-{batch_end}: Created {len(count)} total statistics"
                    )
                else:
                    logger.info(
                        f"  Batch {batch_start}-{batch_end}: No statistics to create"
                    )

            logger.info(f"Completed batch {batch_start}-{batch_end}")
