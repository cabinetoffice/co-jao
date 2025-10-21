# from django.conf import settings
# from django.db import transaction
# from django.utils.log import logging
# from django.db.models import Count
# from django.db.models import Q
# from django.db.models import DecimalField
# from django.db.models import F
# from django.db.models import Max
# from django.db.models import OuterRef
# from django.db.models import Subquery
# from django.db.models.functions import Cast
# from django.contrib.contenttypes.models import ContentType
# from contextlib import suppress
# from django.db.models import Model

# from jao_backend.vacancies.models import Vacancy
# from jao_backend.common.models import ListModel
# from jao_backend.application_statistics.models import AggregatedApplicationStatistic
# from jao_backend.oleeo.models import Dandi, Vacancies
# from jao_backend.oleeo.base_models import NoDestinationModel
# from jao_backend.oleeo.base_querysets import sliding_window_range

# logger = logging.getLogger(__name__)


# def is_list_model(model: Model):
#     with suppress(NoDestinationModel):
#         return issubclass(model.get_destination_model(), ListModel)
#     return False


# def get_related_list_models(model: Model):
#     return {
#         field.name: field.related_model
#         for field in model._meta.fields
#         if getattr(field, "related_model", False) and is_list_model(field.related_model)
#     }


# class OleeoApplicantStatisticsAggregator:
#     def __init__(self, batch_size, initial_vacancy_id):
#         self.batch_size = batch_size
#         self.initial_vacancy_id = initial_vacancy_id

#     def _get_vacancy_statistics_per_characteristic(
#         self, vacancy_id_start, vacancy_id_end, characteristic_field
#     ):
#         # Important to limit this to vacancies that have been ingested locally,
#         # otherwise me may violate foreign key constraints when creating statistics.
#         local_vacancies = [*Vacancy.objects.order_by("pk").filter(
#                                                     pk__gte=vacancy_id_start,
#                                                     pk__lte=vacancy_id_end).values_list("pk", flat=True)
#                            ]
#         field_path = f"applications__dandi__{characteristic_field}"
#         total_apps_subquery = (
#             Vacancies.objects_for_ingest.valid_for_ingest()
#             .filter(
#                 vacancy_id=OuterRef("vacancy_id"),
#                 applications__isnull=False,
#                 applications__dandi__isnull=False,
#             )
#             .annotate(total_count=Count("applications", distinct=True))
#             .values("total_count")
#         )

#         return (
#             Vacancies.objects_for_ingest.valid_for_ingest()
#             .filter(
#                 Q(vacancy_id__gte=vacancy_id_start, vacancy_id__lte=vacancy_id_end) & Q(vacancy_id__in=local_vacancies),
#                 applications__isnull=False,
#                 applications__dandi__isnull=False,
#                 **{f"{field_path}__isnull": False},
#             )
#             .values("vacancy_id", field_path)
#             .annotate(
#                 characteristic_count=Count("applications"),
#                 total_applications=Subquery(total_apps_subquery),
#                 ratio=Cast(
#                     F("characteristic_count") * 1.0 / F("total_applications"),
#                     DecimalField(max_digits=15, decimal_places=14),
#                 ),
#                 latest_updated=Max("applications__dandi__row_last_updated"),
#                 object_id=F(field_path),
#             )
#             .order_by("vacancy_id", field_path)
#         )

#     def _create_statistics_from_characteristic_data(
#         self, characteristic_data, characteristic_field, relations
#     ):
#         src_list_model = relations[characteristic_field]
#         destination_list_model = src_list_model.get_destination_model()
#         content_type = ContentType.objects.get_for_model(destination_list_model)

#         for row in characteristic_data:
#             yield AggregatedApplicationStatistic(
#                 vacancy_id=row["vacancy_id"],
#                 content_type=content_type,
#                 object_id=row["object_id"],
#                 ratio=row["ratio"],
#                 updated_at=row["latest_updated"],
#             )

#     def do_ingest(self):
#         if not settings.JAO_BACKEND_ENABLE_OLEEO:
#             logger.error("OLEEO integration is disabled")
#             raise ValueError("OLEEO integration is not enabled")

#         max_batch_size = (
#             self.batch_size or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
#         )
#         relations = get_related_list_models(Dandi)
#         max_vacancy_id = Vacancy.objects.order_by("pk").last().pk

#         logger.info("Aggregate.. %s", max_vacancy_id)
#         logger.info("Relations found: %s", list(relations.keys()))
#         logger.info("Update aggregated statistics")

#         initial_vacancy_id = (
#             Vacancy.objects.first().pk
#             if self.initial_vacancy_id is None
#             else self.initial_vacancy_id
#         )
#         max_id = Vacancy.objects.last().pk

#         for batch_start, batch_end in sliding_window_range(
#             initial_vacancy_id, max_id, max_batch_size, 0, progress_bar=None
#         ):
#             logger.info(f"Processing batch {batch_start}-{batch_end}")
#             with transaction.atomic():
#                 deleted_count = AggregatedApplicationStatistic.objects.filter(
#                     vacancy_id__gte=batch_start, vacancy_id__lte=batch_end
#                 ).delete()[0]
#                 logger.info(f"  Deleted {deleted_count} existing statistics")

#                 statistics = []
#                 for characteristic_field in relations.keys():
#                     logger.info(f"  Processing {characteristic_field}...")
#                     characteristic_data = (
#                         self._get_vacancy_statistics_per_characteristic(
#                             batch_start, batch_end, characteristic_field
#                         )
#                     )
#                     statistics.extend(
#                         list(
#                             self._create_statistics_from_characteristic_data(
#                                 characteristic_data, characteristic_field, relations
#                             )
#                         )
#                     )

#                 if statistics:
#                     count = AggregatedApplicationStatistic.objects.bulk_create(
#                         statistics
#                     )
#                     logger.info(
#                         f"  Batch {batch_start}-{batch_end}: Created {len(count)} total statistics"
#                     )
#                 else:
#                     logger.info(
#                         f"  Batch {batch_start}-{batch_end}: No statistics to create"
#                     )

#             logger.info(f"Completed batch {batch_start}-{batch_end}")

# ===============================================
# Imports and Helper Functions
# ===============================================
import os
import csv
from collections import defaultdict
from contextlib import suppress

from django.conf import settings
from django.db import transaction
from django.utils.log import logging
from django.db.models import Count, Q, DecimalField, F, Max, OuterRef, Subquery, Model
from django.db.models.functions import Cast
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# Import your models (adjust paths if needed)
from jao_backend.vacancies.models import Vacancy
from jao_backend.common.models import ListModel
# Import BOTH statistics models now
from jao_backend.application_statistics.models import AggregatedApplicationStatistic, AggregatedApplicationCount, Region
from jao_backend.oleeo.models import Dandi, Vacancies # Make sure Dandi is imported from oleeo.models
from jao_backend.oleeo.base_models import NoDestinationModel
from jao_backend.oleeo.base_querysets import sliding_window_range

logger = logging.getLogger(__name__)

# --- Helper functions (used by the original aggregator) ---
def is_list_model(model: Model):
    with suppress(NoDestinationModel):
        # Check if the model has get_destination_model and if it's a subclass of ListModel
        if hasattr(model, 'get_destination_model') and model.get_destination_model():
            return issubclass(model.get_destination_model(), ListModel)
    return False

def get_related_list_models(model: Model):
    """ Finds ForeignKey fields on the model that point to an OleeoUpstreamModel which syncs to a ListModel. """
    relations = {}
    for field in model._meta.get_fields(): # Use get_fields() for modern Django
        if field.is_relation and field.many_to_one and hasattr(field.related_model, 'get_destination_model'):
            # Check if the related model's destination is a ListModel
            if is_list_model(field.related_model):
                relations[field.name] = field.related_model
    return relations

# ===============================================
# Standard D&I Statistics Aggregator (Ratios)
# ===============================================
class OleeoApplicantStatisticsAggregator:
    def __init__(self, batch_size, initial_vacancy_id):
        self.batch_size = batch_size
        self.initial_vacancy_id = initial_vacancy_id

    def _get_vacancy_statistics_per_characteristic(
        self, vacancy_id_start, vacancy_id_end, characteristic_field
    ):
        # Ensure only locally existing vacancies are processed
        local_vacancies = set(Vacancy.objects.filter(
            pk__gte=vacancy_id_start, pk__lte=vacancy_id_end
        ).values_list("pk", flat=True))

        if not local_vacancies:
            return Vacancies.objects_for_ingest.none() # Return empty queryset if no local vacancies

        field_path = f"applications__dandi__{characteristic_field}"
        # Subquery to count distinct applications per vacancy *that provided D&I data*
        # This is crucial for calculating the ratio correctly based on those who answered.
        total_answered_subquery = (
            Vacancies.objects_for_ingest.using('oleeo_upstream') # Specify DB
            .filter(
                vacancy_id=OuterRef("vacancy_id"),
                applications__isnull=False,
                applications__dandi__isnull=False,
                **{f"{field_path}__isnull": False} # Only count apps that answered *this* question
            )
            .annotate(total_count=Count("applications", distinct=True))
            .values("total_count")
        )

        return (
            Vacancies.objects_for_ingest.using('oleeo_upstream') # Specify DB
            # Remove valid_for_ingest() here, apply filters directly
            .filter(
                Q(vacancy_id__gte=vacancy_id_start, vacancy_id__lte=vacancy_id_end) & Q(vacancy_id__in=local_vacancies),
                applications__isnull=False,
                applications__dandi__isnull=False,
                **{f"{field_path}__isnull": False}, # Ensure the characteristic is not null
            )
            .values("vacancy_id", field_path) # Group by vacancy and the characteristic's ID
            .annotate(
                characteristic_count=Count("applications", distinct=True), # Count distinct applications per group
                total_applications_answered=Subquery(total_answered_subquery), # Use the subquery for denominator
                # Calculate ratio based on those who answered this specific question
                ratio=Cast(
                    F("characteristic_count") * 1.0 / F("total_applications_answered"),
                    DecimalField(max_digits=15, decimal_places=14),
                ),
                latest_updated=Max("applications__dandi__row_last_updated"), # Get latest timestamp from Dandi record
                object_id=F(field_path), # The characteristic's ID (e.g., gender_id)
            )
            .filter(total_applications_answered__gt=0) # Avoid division by zero
            .order_by("vacancy_id", field_path)
        )

    def _create_statistics_from_characteristic_data(
        self, characteristic_data, characteristic_field, relations
    ):
        src_list_model = relations[characteristic_field]
        try:
            destination_list_model = src_list_model.get_destination_model()
            content_type = ContentType.objects.get_for_model(destination_list_model)
        except (NoDestinationModel, ContentType.DoesNotExist) as e:
             logger.warning(f"Could not get destination model or ContentType for {characteristic_field}: {e}. Skipping.")
             return # Skip processing if destination/contenttype is missing

        for row in characteristic_data:
             # Ensure ratio is not None before creating the object
             if row.get("ratio") is not None and row.get("object_id") is not None:
                yield AggregatedApplicationStatistic(
                    vacancy_id=row["vacancy_id"],
                    content_type=content_type,
                    object_id=row["object_id"],
                    ratio=row["ratio"],
                    updated_at=row["latest_updated"], # Uses timestamp from Oleeo source
                )
             else:
                 logger.warning(f"Skipping row due to missing ratio or object_id: {row}")


    def do_ingest(self):
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled, cannot ingest standard stats.")
            raise ValueError("OLEEO integration is not enabled")

        max_batch_size = (
            self.batch_size or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
        )
        # Get relations from the Dandi model
        relations = get_related_list_models(Dandi)
        if not relations:
            logger.warning("No relations found on Dandi model for statistics aggregation. Check helper functions.")
            return

        # Determine vacancy range based on local DB
        try:
            first_vacancy = Vacancy.objects.earliest('pk')
            last_vacancy = Vacancy.objects.latest('pk')
        except Vacancy.DoesNotExist:
            logger.warning("No vacancies found in the local database. Skipping statistics aggregation.")
            return

        initial_vacancy_id = (
            first_vacancy.pk
            if self.initial_vacancy_id is None
            else self.initial_vacancy_id
        )
        max_id = last_vacancy.pk

        logger.info(f"Starting standard applicant statistics aggregation from vacancy ID {initial_vacancy_id} to {max_id}.")
        logger.info(f"Relations found for ratio aggregation: {list(relations.keys())}")

        # Pre-fetch ContentTypes for deletion filtering
        stats_content_types_qs = ContentType.objects.none()
        valid_relations = {}
        for field_name, rel_model in relations.items():
            try:
                dest_model = rel_model.get_destination_model()
                ct = ContentType.objects.get_for_model(dest_model)
                stats_content_types_qs |= Q(pk=ct.pk)
                valid_relations[field_name] = rel_model # Keep track of relations with valid ContentTypes
            except (NoDestinationModel, ContentType.DoesNotExist):
                logger.warning(f"Could not get destination/ContentType for relation '{field_name}'. It will be skipped during deletion and processing.")
        
        if not valid_relations:
             logger.warning("No valid relations with ContentTypes found. Stopping aggregation.")
             return
             
        stats_content_types = ContentType.objects.filter(stats_content_types_qs)
        logger.info(f"Will process statistics for ContentTypes: {[ct.model for ct in stats_content_types]}")


        for batch_start, batch_end in sliding_window_range(
            initial_vacancy_id, max_id, max_batch_size, 0, progress_bar=None
        ):
            logger.info(f"Processing standard stats batch {batch_start}-{batch_end}")
            try:
                with transaction.atomic():
                    # Correctly filter by relevant content_types when deleting
                    deleted_count, _ = AggregatedApplicationStatistic.objects.filter(
                        vacancy_id__gte=batch_start,
                        vacancy_id__lte=batch_end,
                        content_type__in=stats_content_types # Only delete relevant stats
                    ).delete()
                    logger.info(f"  Deleted {deleted_count} existing standard statistics for this batch.")

                    statistics_to_create = []
                    # Only loop through relations we know are valid
                    for characteristic_field in valid_relations.keys():
                        logger.info(f"  Processing {characteristic_field}...")
                        characteristic_data = (
                            self._get_vacancy_statistics_per_characteristic(
                                batch_start, batch_end, characteristic_field
                            )
                        )
                        # Ensure data is generated before extending
                        generated_stats = list(
                            self._create_statistics_from_characteristic_data(
                                characteristic_data, characteristic_field, valid_relations
                            )
                        )
                        if generated_stats:
                            statistics_to_create.extend(generated_stats)


                    if statistics_to_create:
                        created_objects = AggregatedApplicationStatistic.objects.bulk_create(
                            statistics_to_create,
                            batch_size=500,
                            ignore_conflicts=True # Add ignore_conflicts for safety
                        )
                        logger.info(
                            f"  Batch {batch_start}-{batch_end}: Created {len(created_objects)} standard statistics."
                        )
                    else:
                        logger.info(
                            f"  Batch {batch_start}-{batch_end}: No new standard statistics to create."
                        )
            except Exception as e:
                logger.error(f"Error processing standard stats batch {batch_start}-{batch_end}: {e}", exc_info=True)
                # Decide if you want to stop or continue on batch error
                continue # Continue to next batch

            logger.info(f"Completed standard stats batch {batch_start}-{batch_end}")
        logger.info("Standard applicant statistics aggregation finished.")


# ===============================================
# Applicant Region Aggregator (Counts)
# ===============================================
class OleeoApplicantRegionAggregator:
    """
    Ingester for processing Oleeo applicant postcodes, mapping them to regions,
    and storing the aggregated counts in the AggregatedApplicationCount table.
    """
    def __init__(self, batch_size, initial_vacancy_id):
        self.batch_size = batch_size
        self.initial_vacancy_id = initial_vacancy_id
        self.region_lookup = {}
        self.region_name_to_object_map = {}
        self.region_content_type = None
        self.aggregated_count_ctype = None

    def _load_region_map(self):
        """Loads the postcode-to-region CSV into the self.region_lookup dictionary."""
        logger.info("Loading postcode-to-region mapping file...")
        # Ensure correct path construction relative to BASE_DIR
        fixture_path = os.path.join(settings.BASE_DIR, 'jao_backend', 'application_statistics', 'fixtures', 'postcode_regions.csv')
        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    outward_code = row.get('Postcode') # Use .get for safety
                    region_name = row.get('NUTS1 region') # Use .get for safety
                    if outward_code and region_name:
                        # Standardize keys and values (strip whitespace)
                        self.region_lookup[outward_code.strip().upper()] = region_name.strip()
            logger.info(f"  Successfully loaded {len(self.region_lookup)} postcode mappings.")
        except FileNotFoundError:
            logger.error(f"CRITICAL: The mapping file was not found at {fixture_path}. Region ingestion cannot proceed.")
            raise
        except KeyError as e:
             logger.error(f"CRITICAL: Missing expected column in {fixture_path}: {e}. Region ingestion cannot proceed.")
             raise

    def _prepare_region_objects(self):
        """Ensures Region objects exist in the DB and maps names to objects."""
        logger.info("Preparing Region lookup objects...")
        unique_region_names = set(self.region_lookup.values())
        if not unique_region_names:
            logger.warning("No regions found in the mapping file.")
            return

        for region_name in unique_region_names:
            # Use update_or_create for robustness
            region_obj, created = Region.objects.update_or_create(
                description=region_name,
                defaults={'last_updated': timezone.now()} # Update timestamp if exists
            )
            self.region_name_to_object_map[region_name] = region_obj
        logger.info(f"  Ensured {len(unique_region_names)} Region objects exist/are updated in the database.")

    def _process_batch(self, vacancy_id_start, vacancy_id_end):
        """Processes applicant data for a single batch of vacancies."""
        logger.info(f"  Querying applicants for vacancies {vacancy_id_start}-{vacancy_id_end}...")
        vacancy_stats = defaultdict(lambda: defaultdict(int))

        # Filter Dandi records for vacancies within the batch that exist locally
        existing_batch_vacancy_ids = set(Vacancy.objects.filter(
            pk__gte=vacancy_id_start, pk__lte=vacancy_id_end
        ).values_list('id', flat=True))

        if not existing_batch_vacancy_ids:
            logger.info("   No existing local vacancies found in this batch range. Skipping Oleeo query.")
            return [] # Return empty list if no vacancies to process

        # Use the 'objects_for_ingest' manager for consistency if defined on Dandi
        queryset = Dandi.objects_for_ingest.using('oleeo_upstream').select_related(
            'application', 'postcode'
        ).filter(
            application__vacancy_id__in=existing_batch_vacancy_ids
        ).iterator(chunk_size=2000)

        processed_count = 0
        for dandi_record in queryset:
            # Safer attribute checking
            postcode_obj = getattr(dandi_record, 'postcode', None)
            if not postcode_obj or not getattr(postcode_obj, 'postcode_desc', None):
                continue

            postcode_str = postcode_obj.postcode_desc.strip()
            if not postcode_str:
                continue

            outward_code = postcode_str.split(' ')[0].upper()
            region_name = self.region_lookup.get(outward_code)

            if region_name:
                # Ensure application and vacancy_id exist before using
                if hasattr(dandi_record, 'application') and dandi_record.application and hasattr(dandi_record.application, 'vacancy_id'):
                    vacancy_id = dandi_record.application.vacancy_id
                    region_obj = self.region_name_to_object_map.get(region_name)
                    if region_obj:
                        vacancy_stats[vacancy_id][region_obj] += 1
                else:
                    logger.debug(f"Skipping Dandi record {dandi_record.pk} due to missing application or vacancy_id link.")

            processed_count += 1
            # Optional: Log progress less frequently for large batches
            # if processed_count % 10000 == 0:
            #     logger.debug(f"   ...processed {processed_count} applicants in batch...")

        logger.info(f"  Processed {processed_count} applicants for this batch, aggregated stats for {len(vacancy_stats)} vacancies.")

        # Prepare AggregatedApplicationCount objects for bulk creation
        counts_to_create = []
        for vacancy_id, region_counts in vacancy_stats.items():
            for region_obj, count in region_counts.items():
                counts_to_create.append(
                    AggregatedApplicationCount(
                        vacancy_id=vacancy_id,
                        content_type=self.region_content_type,
                        object_id=region_obj.pk,
                        count=count,
                        updated_at=timezone.now(), # Use current time for updates
                        polymorphic_ctype=self.aggregated_count_ctype
                    )
                )
        return counts_to_create

    def do_ingest(self):
        """Main method to run the aggregation and ingestion process."""
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled, cannot ingest regions.")
            raise ValueError("OLEEO integration is not enabled")

        # Load mappings and prepare objects once at the start
        try:
            self._load_region_map()
        except Exception as e:
             logger.error(f"Failed to load region map: {e}", exc_info=True)
             # Stop the process if map loading fails
             return
        self._prepare_region_objects()

        # Check if region map or objects are empty after loading/preparation
        if not self.region_lookup or not self.region_name_to_object_map:
            logger.warning("Region lookup map or DB objects are empty/missing. Skipping region aggregation.")
            return

        # Get ContentTypes once
        try:
            self.region_content_type = ContentType.objects.get_for_model(Region)
            self.aggregated_count_ctype = ContentType.objects.get_for_model(AggregatedApplicationCount)
        except ContentType.DoesNotExist as e:
            logger.error(f"Could not find ContentType needed for region aggregation: {e}. Stopping.")
            return


        max_batch_size = (
            self.batch_size or settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
        )

        # Determine the range of vacancies to process based on local DB
        try:
            # Use order_by().first() and order_by().last() for potentially better performance
            first_vacancy = Vacancy.objects.order_by('pk').first()
            last_vacancy = Vacancy.objects.order_by('-pk').first()
            if not first_vacancy or not last_vacancy:
                 raise Vacancy.DoesNotExist # Handle case where Vacancy table is empty
        except Vacancy.DoesNotExist:
            logger.warning("No vacancies found in the local database. Skipping region aggregation.")
            return

        initial_vacancy_id = (
            first_vacancy.pk
            if self.initial_vacancy_id is None
            else self.initial_vacancy_id
        )
        max_id = last_vacancy.pk

        logger.info(f"Starting applicant region aggregation from vacancy ID {initial_vacancy_id} to {max_id}.")

        for batch_start, batch_end in sliding_window_range(
            initial_vacancy_id, max_id, max_batch_size, 0, progress_bar=None # Consider adding tqdm for progress
        ):
            logger.info(f"Processing region counts for batch {batch_start}-{batch_end}")
            try:
                with transaction.atomic():
                    # Delete existing region counts for this batch to avoid duplicates
                    deleted_count, _ = AggregatedApplicationCount.objects.filter(
                        vacancy_id__gte=batch_start,
                        vacancy_id__lte=batch_end,
                        content_type=self.region_content_type # Only delete region stats
                    ).delete()
                    logger.info(f"  Deleted {deleted_count} existing region statistics for this batch.")

                    # Process the batch and get the objects to create
                    statistics_to_create = self._process_batch(batch_start, batch_end)

                    if statistics_to_create:
                        # Bulk create the new statistics
                        created_objects = AggregatedApplicationCount.objects.bulk_create(
                            statistics_to_create,
                            batch_size=500, # Adjust batch size as needed
                            ignore_conflicts=True # Add ignore_conflicts for safety
                        )
                        logger.info(
                            f"  Batch {batch_start}-{batch_end}: Created {len(created_objects)} region count statistics."
                        )
                    else:
                        logger.info(
                            f"  Batch {batch_start}-{batch_end}: No new region statistics to create."
                        )
            except Exception as e:
                # Log any error during the batch processing but continue to the next batch
                logger.error(f"Error processing region counts batch {batch_start}-{batch_end}: {e}", exc_info=True)
                # Depending on requirements, you might want to raise the exception
                # or implement more sophisticated error handling/retries here.
                continue # Continue to the next batch

            logger.info(f"Completed region counts batch {batch_start}-{batch_end}")
        logger.info("Applicant region aggregation finished.")