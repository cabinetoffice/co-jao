from django.conf import settings
from ninja import NinjaAPI
from ninja.security import APIKeyHeader


class ApiKeyAuth(APIKeyHeader):
    """
    API key authentication handler

    Attributes:
        param_name: Header name for API key
    """

    param_name = "X-API-KEY"

    def authenticate(self, request, key):
        """
        Validate API key
        """

        if key in settings.API_KEYS:
            return key  # ToDo: Replace with proper validation
        return None
