from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from litellm import completion

from jao_backend.settings.common import CHAT_MODEL_OPTIONS
from jao_backend.settings.common import LITELLM_CUSTOM_PROVIDER
from jao_backend.settings.common import EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import VacancyEmbedding
from jao_backend.application_statistics.models.lists import Gender, Disability
from jao_backend.application_statistics.models.statistics import AggregatedApplicationStatistic


class Command(BaseCommand):
    help = 'Generate job description advice based on similar vacancies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of similar vacancies to retrieve (default: 10)'
        )

        parser.add_argument(
            '--female-ratio',
            type=float,
            help='Filter vacancies by minimum female applicant ratio (e.g., 0.4 for 40%)'
        )

        parser.add_argument(
            '--disability-ratio',
            type=float,
            help='Filter vacancies by minimum disability applicant ratio (e.g., 0.1 for 10%)'
        )

    def build_filters(self, options):
        filters = Q()

        # Female ratio filter
        if options['female_ratio'] is not None:
            gender_ct = ContentType.objects.get_for_model(Gender)
            female = Gender.objects.get(description__iexact="woman")

            female_vacancy_ids = (
                AggregatedApplicationStatistic.objects
                .filter(
                    content_type=gender_ct,
                    object_id=female.id,
                    ratio__gte=options['female_ratio']
                )
                .values_list("vacancy_id", flat=True)
            )
            filters &= Q(vacancy_id__in=female_vacancy_ids)

        # Disability ratio filter
        if options['disability_ratio'] is not None:
            disability_ct = ContentType.objects.get_for_model(Disability)
            yes = Disability.objects.get(description__iexact="yes")

            disability_vacancy_ids = (
                AggregatedApplicationStatistic.objects
                .filter(
                    content_type=disability_ct,
                    object_id=yes.id,
                    ratio__gte=options['disability_ratio']
                )
                .values_list("vacancy_id", flat=True)
            )
            filters &= Q(vacancy_id__in=disability_vacancy_ids)

        return filters

    def handle(self, *args, **options):
        limit = options['limit']

        self.stdout.write(self.style.SUCCESS('=== Job Description Advice Generator ==='))

        filters = self.build_filters(options)
        if filters.children:
            self.stdout.write(self.style.WARNING("Applied filters."))

        self.stdout.write('Please enter the job description you want to analyze.')
        self.stdout.write('You can paste multiple lines. Press Ctrl+D (or Ctrl+Z on Windows) when done:\n')

        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nOperation cancelled.'))
            return

        job_description = '\n'.join(lines).strip()
        if not job_description:
            self.stdout.write(self.style.ERROR('No job description provided. Exiting.'))
            return

        self.stdout.write(f'\n{self.style.SUCCESS("Analyzing job description...")}')
        self.stdout.write(f'Using {limit} similar vacancies for comparison.\n')

        try:
            tag = EmbeddingTag.get_tag(EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)

            if filters.children:
                similar_vacancies = VacancyEmbedding.objects.similar_vacancies(
                    job_description,
                    tag,
                    top_n=limit,
                    filters=filters
                )
            else:
                similar_vacancies = VacancyEmbedding.objects.similar_vacancies(
                    job_description,
                    tag,
                    top_n=limit
                )

            vacancy_count = len(similar_vacancies)
            self.stdout.write(f'Found {vacancy_count} similar vacancies, generating advice...\n')
            if vacancy_count == 0:
                self.stdout.write(self.style.WARNING('No similar vacancies found with the applied filters.'))
                return

            # Instruction builder
            instructions = []
            if options.get("female_ratio"):
                instructions.append(
                    f"Provide advice to attract more female applicants (≥{options['female_ratio']*100:.0f}%)."
                )
            if options.get("disability_ratio"):
                instructions.append(
                    f"Provide advice to attract more applicants with disabilities (≥{options['disability_ratio']*100:.0f}%)."
                )
            if not instructions:
                instructions.append("Provide actionable advice to improve this job advert using the similar vacancies as context.")

            similar_vacancies_text = "\n".join([
                f"- {v.vacancy.title} (ID {v.vacancy_id})" for v in similar_vacancies
            ])

            prompt = f"""
            Job Description:
            {job_description}

            Similar Vacancies:
            {similar_vacancies_text}

            Instruction:
            {' '.join(instructions)}
            """

            response = completion(
                model=CHAT_MODEL_OPTIONS["ollama"],
                messages=[
                    {"role": "system", "content": "You are an assistant that improves job adverts."},
                    {"role": "user", "content": prompt}
                ],
            )

            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(response["choices"][0]["message"]["content"])
            self.stdout.write(self.style.SUCCESS('='*60))

        except Exception as e:
            raise CommandError(f'Error generating advice: {str(e)}')

