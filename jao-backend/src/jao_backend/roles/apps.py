from django.apps import AppConfig


class RolesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jao_backend.roles"

    def ready(self):
        # Import the ingest schemas to ensure they are registered
        from jao_backend.roles.ingest_schemas.ingest_schema import IngestRoleTypeSchema
