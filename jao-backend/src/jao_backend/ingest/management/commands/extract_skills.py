import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from jao_backend.common.celery import app as celery_app
from jao_backend.applicant_text.models import VacancyTextAggregate
from jao_backend.vacancies.models import Vacancy
from jao_backend.skills.models import Skill
from jao_backend.vacancies.tasks import proxy_extract_from_applicant_text

logger = logging.getLogger(__name__)
BATCH_SIZE = 2000 # We are in test mode


class Command(BaseCommand):
    """
    This command synchronously extracts skills from applicant text,
    saves them, and links them to vacancies.
    """
    help = "Extracts skills from applicant text and links them to Vacancies."

    def handle(self, *args, **options):
        self.stdout.write("Starting skill extraction...")

        # A local cache to avoid thousands of get_or_create DB hits
        skill_object_cache = {skill.name: skill for skill in Skill.objects.all()}

        # We are in TEST MODE (no while True loop)
        # ----------------------------------------
        unprocessed_records = list(
            VacancyTextAggregate.objects.filter(skills_extracted=False)
            .select_related('vacancy')
            .order_by('vacancy_id')
            [:BATCH_SIZE]
        )

        if not unprocessed_records:
            self.stdout.write("No new applicant texts to process.")
            return

        self.stdout.write(f"Processing batch of {len(unprocessed_records)} vacancy texts...")

        # === 1. PREPARE THE TEXT BATCH ===
        batch_of_texts_to_send = []
        for agg_text in unprocessed_records:
            combined_text = " ".join(filter(None, [
                agg_text.all_personal_statements,
                agg_text.all_employment_history,
                agg_text.all_previous_skills
            ]))
            batch_of_texts_to_send.append(combined_text)

        # === 2. SEND TASK TO PYTHON 3.10 WORKER ===
        self.stdout.write("Sending batch to skills-worker...")
        task = proxy_extract_from_applicant_text.apply_async(
        args=[batch_of_texts_to_send],
        queue='skills_queue'
        )
        
        # This is ALLOWED because we are in a command, not a task
        self.stdout.write(f"Task {task.id} sent. Waiting for results...")
        result = task.get(timeout=6000) 

        if result['status'] == 'error':
            self.stderr.write(f"Error from skills-worker: {result['message']}")
            return

        extracted_data = result['data']

        # === 3. SAVE RESULTS TO DATABASE ===
        self.stdout.write("Saving results to database...")
        
        records_to_mark_as_done = []
        
        with transaction.atomic():
            for agg_record, skill_data in zip(unprocessed_records, extracted_data):
                try:
                    vacancy = agg_record.vacancy
                    skill_strings = skill_data['extracted_skills']

                    skills_to_link = []
                    for skill_name in skill_strings:
                        if len(skill_name) > 255:
                            continue
                        if skill_name in skill_object_cache:
                            skill_obj = skill_object_cache[skill_name]
                        else:
                            skill_obj, _ = Skill.objects.get_or_create(name=skill_name)
                            skill_object_cache[skill_name] = skill_obj
                        
                        skills_to_link.append(skill_obj)
                    
                    vacancy.skills.set(skills_to_link)
                    records_to_mark_as_done.append(agg_record.pk)

                except Vacancy.DoesNotExist:
                    self.stderr.write(f"Vacancy {agg_record.vacancy_id} not found. Skipping.")
                except Exception as e:
                    self.stderr.write(f"Error processing {agg_record.vacancy_id}: {e}")

            VacancyTextAggregate.objects.filter(
                pk__in=records_to_mark_as_done
            ).update(skills_extracted=True)

        self.stdout.write(self.style.SUCCESS("Skill extraction complete!"))