from django.urls import path
from jao_backend.healthcheck.views import health_check

urlpatterns = [
    path("", health_check, name="health_check"),
]
