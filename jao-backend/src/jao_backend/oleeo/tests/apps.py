from django.apps import AppConfig


class OleeoTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jao_backend.oleeo.tests"
    database = "default"
