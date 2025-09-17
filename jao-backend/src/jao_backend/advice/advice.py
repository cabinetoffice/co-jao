from litellm import APIConnectionError, completion
from django.conf import settings
import logging

LITELLM_API_BASE = settings.LITELLM_API_BASE
LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER
LITELLM_COMPLETION_MODEL = settings.LITELLM_COMPLETION_MODEL

logger = logging.getLogger(__name__)


def get_advice(user_input, similar_vacancies):

    model_name = getattr(settings, 'LITELLM_COMPLETION_MODEL', 'gpt-3.5-turbo')

    context = "\n\n".join(
        [f"Job Ad {i+1}:\n{ad}" for i, ad in enumerate(similar_vacancies)])

    # Create your prompt
    prompt = f"""You are an expert career advisor and recruiter. Based on these similar job postings, provide specific, actionable advice.

        SIMILAR JOB POSTINGS: {context}

        ANALYSIS REQUEST: {user_input}


        Please provide:
            1. Key insights based on patterns in these postings
            2. Specific recommendations with examples from the postings
            3. Prioritized action items for improvement

        Keep your advice practical and specific. Reference examples from the job postings to support your recommendations.

        Answer:"""
    try:
        # Use the same configuration pattern as your embedding function
        response = completion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
            api_base=LITELLM_API_BASE,
            custom_llm_provider=LITELLM_CUSTOM_PROVIDER,
        )

        return response.choices[0].message.content

    except APIConnectionError as e:
        logger.error(
            "Connection refused to the completion service. "
            "Ensure the service is running and accessible: %s",
            e,
        )
        raise
    except Exception as e:
        logger.error(f"Error generating advice with LiteLLM: {str(e)}")
        return "Sorry, I'm unable to generate advice at the moment. Please try again later."
