import json
from functools import cache

from django.conf import settings
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.urls import path, reverse

from litellm import APIConnectionError, embedding

from jao_backend.common.admin import ReadOnlyAdminMixin
from jao_backend.common.litellm.model_list import (
    get_available_models,
    get_errors,
)

from .forms import LiteLLMEmbeddingTestForm
from .models import EmbeddingModel, EmbeddingTag


def model_list_view(request):
    """Admin view to display available models from the configured provider."""
    errors = get_errors()
    models = get_available_models()

    for error in errors:
        messages.error(request, error)

    context = {
        **admin.site.each_context(request),
        "title": "Available Embedding Models",
        "opts": EmbeddingModel._meta,  # Use the model's _meta for breadcrumbs
        "models": models,
        "errors": errors,
        "provider": settings.LITELLM_CUSTOM_PROVIDER.capitalize(),
    }
    return TemplateResponse(request, "admin/embeddings/model_list.html", context)


def litellm_test_view(request):
    """Admin view to test the LiteLLM embedding service."""
    form = LiteLLMEmbeddingTestForm(request.POST or None)
    model_list_url = reverse("admin:embeddings_model_list")
    context = {
        **admin.site.each_context(request),
        "title": "LiteLLM Embedding Test",
        "form": form,
        "result": None,
        "error": None,
        "model_list_url": model_list_url,
    }

    if request.method == "POST" and form.is_valid():
        model = form.cleaned_data["model"]
        text = form.cleaned_data["text"]
        try:
            response = embedding(
                model=model,
                input=[text],
                api_base=settings.LITELLM_API_BASE,
                custom_llm_provider=settings.LITELLM_CUSTOM_PROVIDER,
            )
            result_data = response.dict()
            context["result"] = json.dumps(result_data, indent=2)
            messages.success(request, "Embedding successful!")
        except APIConnectionError as e:
            error_message = (
                "API Connection Error: Could not connect to the embedding service. "
                f"Please ensure it's running and accessible. Details: {e}"
            )
            context["error"] = error_message
            messages.error(request, error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            context["error"] = error_message
            messages.error(request, error_message)

    return TemplateResponse(request, "admin/embeddings/litellm_test.html", context)


@admin.register(EmbeddingTag)
class EmbeddingTagAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "model", "version", "description")
    list_filter = ("model",)
    search_fields = ("name", "description")
    readonly_fields = ("uuid",)


@admin.register(EmbeddingModel)
class EmbeddingModelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "is_active")


@cache
def add_admin_urls():
    """
    Django admin doesn't provide a way of adding extra urls, so patch it here.

    lru_cache is used to ensure this function is only run once.
    """
    original_get_urls = admin.site.get_urls
    extra_urls = [
        path(
            "embeddings/litellm-test/",
            admin.site.admin_view(litellm_test_view),
            name="embeddings_litellm_test",
        ),
        path(
            "embeddings/model-list/",
            admin.site.admin_view(model_list_view),
            name="embeddings_model_list",
        ),
    ]

    def get_urls():
        return [*extra_urls, *original_get_urls()]

    admin.site.get_urls = get_urls


add_admin_urls()
