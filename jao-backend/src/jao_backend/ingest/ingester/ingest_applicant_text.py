import logging
from django.conf import settings
from django.db import transaction

from jao_backend.oleeo.base_querysets import sliding_window_range 
from jao_backend.vacancies.models import Vacancy
from jao_backend.applicant_text.models import ApplicationText, VacancyTextAggregate
from jao_backend.oleeo.models import Applications as OleeoApplication

DEFAULT_BATCH_SIZE = settings.JAO_BACKEND_INGEST_DEFAULT_BATCH_SIZE
logger = logging.getLogger(__name__)


class ApplicantTextIngest:
    """
    Ingests raw applicant text from Oleeo and aggregates it by vacancy.
    
    This is a two-step process, run in batches:
    1. Ingest raw text from oleeo.Applications -> applicant_text.ApplicationText
    2. Aggregate text from applicant_text.ApplicationText -> applicant_text.VacancyTextAggregate
    """

    def __init__(self, batch_size=DEFAULT_BATCH_SIZE, initial_vacancy_id=None, **kwargs):
        """ This __init__ matches the style of your OleeoVacanciesIngest """
        self.batch_size = batch_size
        self.initial_vacancy_id = initial_vacancy_id

    def do_ingest(self, progress_bar=None):
        """
        Main method to run the ingestion and aggregation.
        This loops through vacancy batches, similar to your region aggregator.
        """
        if not settings.JAO_BACKEND_ENABLE_OLEEO:
            logger.error("OLEEO integration is disabled, cannot ingest applicant text.")
            raise ValueError("OLEEO integration is not enabled")


        try:
            first_vacancy = Vacancy.objects.order_by('pk').first()
            last_vacancy = Vacancy.objects.order_by('-pk').first()
            if not first_vacancy:
                 raise Vacancy.DoesNotExist
        except Vacancy.DoesNotExist:
            logger.warning("No vacancies found in local database. Skipping applicant text ingest.")
            return

        initial_vacancy_id = self.initial_vacancy_id or first_vacancy.pk
        max_id = last_vacancy.pk

        logger.info(f"Starting applicant text ingest from vacancy ID {initial_vacancy_id} to {max_id}.")


        for batch_start, batch_end in sliding_window_range(
            initial_vacancy_id, max_id, self.batch_size, 0, progress_bar=progress_bar
        ):
            logger.info(f"Processing applicant text for batch {batch_start}-{batch_end}")
            try:
                with transaction.atomic():

                    self._ingest_raw_text(batch_start, batch_end)
                    

                    self._aggregate_text_for_batch(batch_start, batch_end)
                    
            except Exception as e:
                logger.error(f"Error processing applicant text batch {batch_start}-{batch_end}: {e}", exc_info=True)
                continue 
        
        logger.info("Applicant text ingestion and aggregation finished.")

    def _ingest_raw_text(self, vacancy_id_start, vacancy_id_end):
        """
        [Step 1] Extracts from Oleeo and loads into our 'raw' ApplicationText table.
        """
        logger.info(f"  Ingesting raw text...")

        existing_batch_vacancy_ids = set(Vacancy.objects.filter(
            pk__gte=vacancy_id_start, pk__lte=vacancy_id_end
        ).values_list('id', flat=True))

        if not existing_batch_vacancy_ids:
            logger.info("   No local vacancies in this batch. Skipping raw text ingest.")
            return

        deleted_count, _ = ApplicationText.objects.filter(
            vacancy_id__in=existing_batch_vacancy_ids
        ).delete()
        logger.info(f"   Deleted {deleted_count} existing raw text records for this batch.")

        oleeo_apps = OleeoApplication.objects_for_ingest.using('oleeo_upstream').filter(
            vacancy_id__in=existing_batch_vacancy_ids
        ).iterator()

        to_create = []
        for app in oleeo_apps:
            to_create.append(
                ApplicationText(
                    vacancy_id=app.vacancy_id,
                    application_id=app.application_id,
                    personal_statement=app.personal_statement,
                    employment_history=app.employment_history,
                    previous_skill_experience=app.previous_skill_experience,
                )
            )

        if to_create:
            created_objects = ApplicationText.objects.bulk_create(to_create, batch_size=500)
            logger.info(f"   Ingested {len(created_objects)} raw text records.")
        else:
            logger.info("   No new raw text records to ingest.")

    def _aggregate_text_for_batch(self, vacancy_id_start, vacancy_id_end):
        """
        [Step 2] Aggregates text from 'raw' table into 'aggregate' table.
        """
        logger.info(f"  Aggregating text...")
        SEPARATOR = "\n\n---APPLICATION BREAK---\n\n"

        deleted_count, _ = VacancyTextAggregate.objects.filter(
            vacancy_id__gte=vacancy_id_start,
            vacancy_id__lte=vacancy_id_end,
        ).delete()
        logger.info(f"   Deleted {deleted_count} existing aggregated text records for this batch.")
        
        vacancy_ids_to_agg = set(ApplicationText.objects.filter(
            vacancy_id__gte=vacancy_id_start,
            vacancy_id__lte=vacancy_id_end
        ).values_list('vacancy_id', flat=True))
        
        if not vacancy_ids_to_agg:
            logger.info("   No raw text found in this batch to aggregate. Skipping.")
            return

        to_create_agg = []
        for vacancy_id in vacancy_ids_to_agg:
            raw_texts = ApplicationText.objects.filter(vacancy_id=vacancy_id)

            all_statements = SEPARATOR.join(
                [app.personal_statement for app in raw_texts if app.personal_statement]
            )
            all_history = SEPARATOR.join(
                [app.employment_history for app in raw_texts if app.employment_history]
            )
            all_skills = SEPARATOR.join(
                [app.previous_skill_experience for app in raw_texts if app.previous_skill_experience]
            )

            to_create_agg.append(
                VacancyTextAggregate(
                    vacancy_id=vacancy_id,
                    all_personal_statements=all_statements,
                    all_employment_history=all_history,
                    all_previous_skills=all_skills,
                )
            )

        if to_create_agg:
            created_objects = VacancyTextAggregate.objects.bulk_create(to_create_agg, batch_size=500)
            logger.info(f"   Created {len(created_objects)} aggregated text records.")
        else:
            logger.info("   No aggregated text records to create.")