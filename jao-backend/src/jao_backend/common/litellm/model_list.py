from abc import ABC, abstractmethod
from typing import List, Dict, Type, Tuple

from django.conf import settings, ImproperlyConfigured
import requests
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import logging

logger = logging.getLogger(__name__)

LITELLM_CUSTOM_PROVIDER = settings.LITELLM_CUSTOM_PROVIDER
BEDROCK_REGION = settings.JAO_BEDROCK_REGION


# List available models by querying the model provider.
# LiteLLM doesn't currently provide this.


class ModelListProviderError(Exception):
    pass


class ModelListBase(ABC):
    LITELLM_MODEL_PREFIX = ""

    @classmethod
    @abstractmethod
    def get_model_list(cls) -> List[str]:
        """:return: A list of available model IDs."""
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        pass

    @classmethod
    def get_litellm_model_name(cls, model_name: str) -> str:
        """:return: The model name formatted for use with LiteLLM."""
        if cls.LITELLM_MODEL_PREFIX:
            return f"{cls.LITELLM_MODEL_PREFIX}/{model_name}"
        return model_name

    @classmethod
    def get_litellm_model_list(cls) -> List[Tuple[str, str]]:
        """:return: A list of available model IDs, formatted for LiteLLM."""
        return [
            (model, cls.get_litellm_model_name(model)) for model in cls.get_model_list()
        ]


class OllamaModelList(ModelListBase):
    """Provides a list of models from a local Ollama server."""

    BASE_URL = "http://localhost:11434"
    LITELLM_MODEL_PREFIX = "ollama"

    @classmethod
    def get_model_list(cls) -> List[str]:
        """Fetches model tags from the Ollama API."""
        url = f"{cls.BASE_URL}/api/tags"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            models_data = response.json().get("models", [])
            return [model["name"] for model in models_data]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama server: {e}")
            raise ModelListProviderError(
                f"Ollama server is not reachable at {url}"
            ) from e

    @classmethod
    def is_available(cls) -> bool:
        """Checks if the Ollama server is running."""
        try:
            return requests.get(f"{cls.BASE_URL}/", timeout=2).status_code == 200
        except requests.exceptions.RequestException:
            logger.error(f"Ollama server is not available at {cls.BASE_URL}")
            return False


class BedrockModelList(ModelListBase):
    """Provides a list of models from AWS Bedrock."""

    # Bedrock uses the model ID directly, so the prefix is empty.
    LITELLM_MODEL_PREFIX = ""

    @classmethod
    def get_model_list(cls) -> List[str]:
        try:
            logger.info("Fetch bedrock model list for region %s", BEDROCK_REGION)
            client = boto3.client("bedrock", region_name=BEDROCK_REGION)
            response = client.list_foundation_models()
            return [model["modelId"] for model in response.get("modelSummaries", [])]
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to fetch Bedrock models due to AWS error: {e}")
            raise ModelListProviderError(
                f"AWS Bedrock is not reachable in region: {BEDROCK_REGION} or credentials are invalid."
            ) from e

    @classmethod
    def is_available(cls) -> bool:
        try:
            client = boto3.client("bedrock", region_name=BEDROCK_REGION)
            client.list_foundation_models(maxResults=1)
            return True
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Bedrock not available: {e}")
            return False


class LlamaCPPModelList(ModelListBase):
    """Provides a list of models from a local Llama.cpp server."""

    BASE_URL = "http://localhost:8080"  # Default for llama-cpp-python
    LITELLM_MODEL_PREFIX = "llama-cpp"

    @classmethod
    def get_model_list(cls) -> List[str]:
        """Fetches model IDs from the Llama.cpp OpenAI-compatible API."""
        url = f"{cls.BASE_URL}/v1/models"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            models_data = response.json().get("data", [])
            return [model["id"] for model in models_data]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Llama.cpp server: {e}")
            raise ModelListProviderError(
                f"Llama.cpp server is not reachable at {url}"
            ) from e

    @classmethod
    def is_available(cls) -> bool:
        """Checks if the Llama.cpp server is running and responsive."""
        try:
            # A request to the models endpoint is a reliable check
            return (
                requests.get(f"{cls.BASE_URL}/v1/models", timeout=2).status_code == 200
            )
        except requests.exceptions.RequestException:
            logger.error(f"Llama.cpp server is not available at {cls.BASE_URL}")
            return False


def get_model_lister() -> Type[ModelListBase]:
    model_listers: Dict[str, Type[ModelListBase]] = {
        "ollama": OllamaModelList,
        "bedrock": BedrockModelList,
        "llama-cpp": LlamaCPPModelList,
    }
    try:
        return model_listers[LITELLM_CUSTOM_PROVIDER]
    except KeyError:
        raise ImproperlyConfigured(
            f"Unsupported LITELLM_CUSTOM_PROVIDER: '{LITELLM_CUSTOM_PROVIDER}'. "
            f"Currently only {list(model_listers.keys())} are supported."
        )


ModelLister = get_model_lister()


def get_available_models() -> List[str]:
    """
    Fetches the list of models from the configured provider.
    :raises ModelListProviderError: If the provider is unavailable or an API error occurs.
    :return: A list of model ID strings.
    """
    try:
        return ModelLister.get_litellm_model_list()
    except ModelListProviderError as e:
        return []


def get_errors() -> List[str]:
    """
    Checks the configured provider for availability and connection errors.
    :return: A list of error messages, or an empty list if no errors are found.
    """
    if not ModelLister.is_available():
        return [
            f"The '{LITELLM_CUSTOM_PROVIDER}' provider is not configured or reachable."
        ]

    try:
        ModelLister.get_model_list()
    except ModelListProviderError as e:
        return [f"Error fetching model list: {e}"]

    return []
