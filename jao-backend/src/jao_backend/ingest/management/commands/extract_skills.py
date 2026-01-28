import logging

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from jao_backend.applicant_text.models import VacancyTextAggregate
from jao_backend.vacancies.models import Vacancy
from jao_backend.skills.models import Skill

logger = logging.getLogger(__name__)
BATCH_SIZE = 2000


class Command(BaseCommand):
    help = "Extract skills from applicant text via the skills-worker HTTP service."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE,
            help="Number of vacancy texts to process per batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        skills_worker_url = getattr(settings, 'SKILLS_WORKER_URL', 'http://skills-worker:5000')

        self.stdout.write("Starting skill extraction...")

        skill_object_cache = {skill.name: skill for skill in Skill.objects.all()}

        unprocessed_records = list(
            VacancyTextAggregate.objects.filter(skills_extracted=False)
            .select_related('vacancy')
            .order_by('vacancy_id')
            [:batch_size]
        )

        if not unprocessed_records:
            self.stdout.write("No new applicant texts to process.")
            return

        self.stdout.write(f"Processing batch of {len(unprocessed_records)} vacancy texts...")

        batch_of_texts_to_send = []
        for agg_text in unprocessed_records:
            combined_text = " ".join(filter(None, [
                agg_text.all_personal_statements,
                agg_text.all_employment_history,
                agg_text.all_previous_skills
            ]))
            batch_of_texts_to_send.append(combined_text)

        self.stdout.write(f"Sending batch to skills-worker at {skills_worker_url}...")

        try:
            with httpx.Client(timeout=600.0) as client:
                response = client.post(
                    f"{skills_worker_url}/extract",
                    json={"texts": batch_of_texts_to_send}
                )
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            self.stderr.write(f"HTTP error calling skills-worker: {e}")
            return
        except Exception as e:
            self.stderr.write(f"Error calling skills-worker: {e}")
            return

        if result.get('status') == 'error':
            self.stderr.write(f"Error from skills-worker: {result.get('message')}")
            return

        extracted_data = result['data']

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

        self.stdout.write(self.style.SUCCESS(f"Processed {len(records_to_mark_as_done)} vacancy texts"))
