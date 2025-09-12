from django.urls import path

from .views import exception_view

app_name = "inline_exceptions"

urlpatterns = [
    path("exception/<str:exc_id>/", exception_view, name="exception_view"),
]
