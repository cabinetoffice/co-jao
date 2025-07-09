from django.apps import AppConfig


class OleeoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jao_backend.oleeo"

    def ready(self):
        """
        This method is called when the application is ready.
        It can be used to perform any initialization tasks.
        """
        # Ensure that schemas are registered by importing from the module
        from jao_backend.oleeo.ingest_schemas.ingest_schema import IngestAgeGroups
