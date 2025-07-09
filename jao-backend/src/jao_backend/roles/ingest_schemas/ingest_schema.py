from typing import Union

from pydantic import Field
from pydantic import field_validator

from jao_backend.ingest.ingester.schema_registry import register_upstream_mapping
from jao_backend.roles.ingest_schemas.django_schema import GradeSchema
from jao_backend.roles.ingest_schemas.django_schema import RoleTypeSchema


@register_upstream_mapping
class IngestRoleTypeSchema(RoleTypeSchema):
    """RoleType schema for ingestion purposes.

    No data transforms take place, the ingest purely
    """

    model_config = RoleTypeSchema.model_config.copy()
    model_config["model"] = RoleTypeSchema.model_config["model"]

    @field_validator("description", mode="before")  # noqa
    @classmethod
    def validate_description(cls, value: Union[str, list]) -> str:
        """
        Shorthand is an array, this has been filtered to only include rows
        with a single item.
        """
        return value[0] if value else None


@register_upstream_mapping
class IngestGradeSchema(GradeSchema):
    """Grade schema for ingestion purposes."""

    shorthand_name: str = Field(alias="shorthand")

    model_config = GradeSchema.model_config.copy()
    model_config["model"] = GradeSchema.model_config["model"]

    @field_validator("description", mode="before")  # noqa
    @classmethod
    def validate_description(cls, value: Union[str, list]) -> str:
        """
        Shorthand is an array, this has been filtered to only include rows
        with a single item.
        """
        return value[0] if value else None

    @field_validator("shorthand_name", mode="before")  # noqa
    @classmethod
    def validate_shorthand(cls, value: Union[str, list]) -> str:
        """
        Shorthand is an array, this has been filtered to only include rows
        with a single item.
        """
        return value[0] if value else None
