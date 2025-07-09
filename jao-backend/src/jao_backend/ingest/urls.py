from django.urls import path

from .views import IngestStatusView

urlpatterns = [
    path("", IngestStatusView.as_view(), name="ingest_status"),
]
