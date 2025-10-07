from litellm import APIConnectionError, completion
from django.conf import settings
import logging
import json

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import VacancyEmbedding
from jao_backend.application_statistics.models.lists import Gender, Disability
from jao_backend.application_statistics.models.statistics import AggregatedApplicationStatistic
from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.draft import DraftResponse
from jao_backend.settings.common import EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
from jao_backend.llm.prompts import ADVICE_PROMPTS, DRAFT_PROMPT

LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER
LITELLM_COMPLETION_MODEL = settings.LITELLM_COMPLETION_MODEL

logger = logging.getLogger(__name__)


class LLMService():

    def __init__(self):
        self.tag = EmbeddingTag.get_tag(
            EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)
        self.prompt_ids = {
            "general": "general",
            "gender": "gender",
            "disability": "disability"
        }
        self.model = getattr(
            settings, 'LITELLM_COMPLETION_MODEL', 'gpt-3.5-turbo')
        self.rag_content_limit = 10

    def build_filters(self, options):
        filters = Q()

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

    def _update_rag_content(self, user_input, filters):
        updated_vacancies = VacancyEmbedding.objects.similar_vacancies(
            user_input, self.tag, top_n=self.rag_content_limit, filters=filters
        )
        vacancy_count = len(updated_vacancies)
        if vacancy_count == 0:
            raise Exception(self.style.WARNING(
                'No similar vacancies found with the applied filters.'))
        return updated_vacancies

    def _draft_handler(self, user_input, rag_content):

        prompt_config = DRAFT_PROMPT

        messages = [
            {"role": "system", "content": prompt_config["system"]},
            {"role": "user", "content": prompt_config["user_template"].format(
                rag_content=rag_content,
                user_input=user_input
            )}
        ]

        try:
            return completion(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=1500,
                api_base=LITELLM_API_BASE,
                custom_llm_provider=LITELLM_CUSTOM_PROVIDER
            )
        except Exception as e:
            logger.error(f'Error generating advice: {str(e)}')
            raise

    def _advice_handler(self, user_input, rag_content, advice_type, options=None):
        if advice_type != "general" and options:
            filters = self.build_filters(options)
            try:
                updated_vacancies = self._update_rag_content(
                    user_input, filters)
                rag_content = "\n\n".join(
                    [f"Job Ad {v.vacancy.job_title}:\n{v.vacancy.full_job_desc}"
                     for v in enumerate(updated_vacancies)]
                )
            except Exception as e:
                logger.error(f'Error filtering vacancies: {str(e)}')

        prompt_config = ADVICE_PROMPTS.get(advice_type)
        if not prompt_config:
            raise ValueError(f"Unknown advice type: {advice_type}")

        messages = [
            {"role": "system", "content": prompt_config["system"]},
            {"role": "user", "content": prompt_config["user_template"].format(
                rag_content=rag_content,
                user_input=user_input
            )}
        ]

        try:
            return completion(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=1500,
                api_base=LITELLM_API_BASE,
                custom_llm_provider=LITELLM_CUSTOM_PROVIDER
            )
        except Exception as e:
            logger.error(f'Error generating advice: {str(e)}')
            raise

    def get_advice(self, user_input, similar_vacancies, advice_type,
                   options=None):
        rag_content = "\n\n---\n\n".join(similar_vacancies)
        try:
            response = self._advice_handler(
                user_input, rag_content, advice_type, options)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except APIConnectionError as e:
            logger.error(
                "Connection refused to the completion service. "
                "Ensure the service is running and accessible: %s",
                e,
            )
            raise
        except Exception as e:
            logger.error(f"Error generating advice with LiteLLM: {str(e)}")
            yield "Sorry, I'm unable to generate advice at the moment. Please try again later."

    def generate_draft(self, user_input, similar_vacancies):
        rag_content = "\n\n---\n\n".join(similar_vacancies)
        try:
            response = self._draft_handler(
                user_input, rag_content)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except APIConnectionError as e:
            logger.error(
                "Connection refused to the completion service. "
                "Ensure the service is running and accessible: %s",
                e,
            )
            raise
        except Exception as e:
            logger.error(f"Error generating advice with LiteLLM: {str(e)}")
            yield "Sorry, I'm unable to generate drafts at the moment. Please try again later."
