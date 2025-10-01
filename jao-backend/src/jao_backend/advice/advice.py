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
from jao_backend.settings.common import EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID
from .prompts import GENERAL_ADVICE_PROMPT, GENDER_BALANCE_PROMPT, DISABILITY_BALANCE_PROMPT

LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER
LITELLM_COMPLETION_MODEL = settings.LITELLM_COMPLETION_MODEL

logger = logging.getLogger(__name__)


class AdviceService():

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

    def _get_advice_for_type(self, user_input, rag_content):
        return completion(
            model=self.model,
            prompt_id=self.prompt_ids["general"],
            prompt_variables={"user_input": user_input,
                              "vacancies": rag_content},
            stream=True,
            max_tokens=1500,
            api_base=LITELLM_API_BASE,
            custom_llm_provider=LITELLM_CUSTOM_PROVIDER
        )

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
            user_input, self.tag, top_n=self.rag_object_limit, filters=filters
        )
        vacancy_count = len(updated_vacancies)
        self.stdout.write(
            f'Found {vacancy_count} updated vacancies, generating advice...\n')
        if vacancy_count == 0:
            raise Exception(self.style.WARNING(
                'No similar vacancies found with the applied filters.'))
        return updated_vacancies

    def _advice_handler(self, user_input, rag_content, advice_type, options=None):
        prompt_id = self.prompt_ids[f"{advice_type}"]
        try:
            if prompt_id == "general":
                return completion(
                    model=self.model,
                    prompt_id=prompt_id,
                    prompt_variables={"user_input": user_input,
                                      "vacancies": rag_content},
                    stream=True,
                    max_tokens=1500,
                    api_base=LITELLM_API_BASE,
                    custom_llm_provider=LITELLM_CUSTOM_PROVIDER
                )
            else:
                filters = self.build_filters(options)
                updated_rag_content = self._updated_rag_content(self,
                                                                user_input,
                                                                filters)
                return completion(
                    model=self.model,
                    prompt_id=prompt_id,
                    prompt_variables={"user_input": user_input,
                                      "vacancies": rag_content},
                    stream=True,
                    max_tokens=1500,
                    api_base=LITELLM_API_BASE,
                    custom_llm_provider=LITELLM_CUSTOM_PROVIDER
                )

        except Exception as e:
            raise Exception(f'Error generating advice: {str(e)}')

    def get_advice(self, user_input, similar_vacancies, advice_type,
                   options=None):
        rag_content = "\n\n".join(
            [f"Job Ad {i+1}:\n{ad}" for i, ad in enumerate(similar_vacancies)])

        try:
            response = self._advice_handler(
                self, user_input, rag_content, advice_type)
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
