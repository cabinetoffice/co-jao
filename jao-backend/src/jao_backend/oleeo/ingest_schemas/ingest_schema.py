from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

from django.utils import dateparse
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from jao_backend.application_statistics.ingest_schemas.django_schema import (
    AgeGroupSchema,
)
from jao_backend.application_statistics.ingest_schemas.django_schema import (
    DisabilitySchema,
)
from jao_backend.application_statistics.ingest_schemas.django_schema import (
    EthnicGroupSchema,
)
from jao_backend.application_statistics.ingest_schemas.django_schema import (
    EthnicitySchema,
)
from jao_backend.application_statistics.ingest_schemas.django_schema import GenderSchema
from jao_backend.application_statistics.ingest_schemas.django_schema import (
    ReligionSchema,
)
from jao_backend.application_statistics.ingest_schemas.django_schema import (
    SexualOrientationSchema,
)
from jao_backend.ingest.ingester.schema_registry import register_model_transform
from jao_backend.roles.ingest_schemas.django_schema import OleeoGradeGroupSchema
from jao_backend.roles.ingest_schemas.django_schema import OleeoRoleTypeSchema
from jao_backend.vacancies.ingest_schemas.django_schema import (
    VacancySchema,
    AggregatedStatisticSchema,
)


def parse_datetime(value: datetime) -> datetime:
    """Ensure that last_updated is in the correct format."""
    if isinstance(value, str):
        # Coerce to iso8601 format
        return dateparse.parse_datetime(value)
    return value


def parse_comma_seperated_list(value: Union[str, list]) -> list:
    """Convert a comma-separated string to a list."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def list_mixin_schema_factory(
    key_prefix: str = "", override_annotations: Optional[dict] = None
) -> Type:
    """Factory to build a ModelSchema to map OLEEO List tables to JAO models.

    In detail:

    Renames fields by stripping a specified prefix from them.

    This is used to map the OLEEO tables which all have fields named with a table specific prefix,
    e.g. the List_AgeGroup has age_group_id, age_group_desc, these can be stripped.

    To use this factory, the source OLEEO table must have at least id, {prefix}_desc and row_last_updated
    columns.

    Factory function to create a ListSchemaMixin with the specified key_prefix.

    Args:
        key_prefix: The prefix to use for field aliases (e.g., "age_group_", "job_role_")

    Returns:
        A dynamically created mixin class with properly configured field aliases

    :key_prefix: str
    :override_annotations: Optionally override default pydantic types.
    """

    def __str__(self) -> str:
        return self.description

    annotations = {
        "id": int,
        "description": str,
        "last_updated": datetime,
    }
    annotations.update(override_annotations or {})

    class_attrs: Dict[str, Any] = {
        "model_config": ConfigDict(populate_by_name=True),
        "id": Field(alias=f"{key_prefix}id"),
        "description": Field(alias=f"{key_prefix}desc"),
        "last_updated": Field(alias="row_last_updated"),
        "validate_last_updated": field_validator("last_updated")(parse_datetime),
        "__doc__": "Generate pydantic model schema for OLEEO List tables.",
        "__str__": __str__,
        "__annotations__": annotations,
    }

    return type(f"ListSchemaMixin{key_prefix.rstrip('_').title()}", (), class_attrs)


@register_model_transform
class IngestAgeGroups(list_mixin_schema_factory("age_group_"), AgeGroupSchema):
    """Map from OLEEO ListAgeGroup field names to JAO names."""

    pass


@register_model_transform
class IngestDisabilities(list_mixin_schema_factory("disability_"), DisabilitySchema):
    """Map from OLEEO ListDisability field names to JAO names."""

    pass


@register_model_transform
class IngestEthnicGroup(list_mixin_schema_factory("ethnic_group_"), EthnicGroupSchema):
    """Map from OLEEO ListEthnicGroup field names to JAO names."""

    pass


@register_model_transform
class IngestEthnicity(list_mixin_schema_factory("ethnicity_"), EthnicitySchema):
    """Map from OLEEO ListEthnicity field names to JAO names."""

    pass


@register_model_transform
class IngestGender(list_mixin_schema_factory("gender_"), GenderSchema):
    """Map from OLEEO ListGender field names to JAO names."""

    pass


@register_model_transform
class IngestOleeoGradeGroup(
    list_mixin_schema_factory("job_grade_", override_annotations={"description": list}),
    OleeoGradeGroupSchema,
):
    """Map from OLEEO ListJobGrade field names to JAO names."""

    shorthand: list = Field(alias="job_grade_shorthand")

    @field_validator("description", mode="before")  # noqa
    @classmethod
    def validate_description(cls, value: Union[str, list]) -> list:
        """Convert comma-separated string to list."""
        return parse_comma_seperated_list(value)

    @field_validator("shorthand", mode="before")  # noqa
    @classmethod
    def validate_shorthand(cls, value: Union[str, list]) -> list:
        """Convert comma-separated string to list."""
        return parse_comma_seperated_list(value)


@register_model_transform
class IngestReligion(list_mixin_schema_factory("religion_"), ReligionSchema):
    """Map from OLEEO ListReligion field names to JAO names."""

    pass


@register_model_transform
class IngestRoleType(
    list_mixin_schema_factory(
        "type_of_role_", override_annotations={"description": list}
    ),
    OleeoRoleTypeSchema,
):
    """Map from OLEEO ListRoleType field names to JAO names."""

    @field_validator("description", mode="before")  # noqa
    @classmethod
    def validate_description(cls, value: Union[str, list]) -> list:
        """Convert comma-separated string to list."""
        return parse_comma_seperated_list(value)


@register_model_transform
class IngestSexualOrientation(
    list_mixin_schema_factory("sexual_orientation_"), SexualOrientationSchema
):
    """Map from OLEEO ListSexualOrientation field names to JAO names."""

    pass


@register_model_transform
class IngestVacancy(VacancySchema):
    """Map from OLEEO ListVacancy field names to JAO names."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(alias="vacancy_id")
    last_updated: datetime = Field(alias="row_last_updated")

    min_salary: Optional[Decimal] = Field(alias="salary_minimum")
    max_salary: Optional[Decimal] = Field(alias="salary_maximum_optional")

    title: str = Field(alias="vacancy_title")
    description: Optional[str] = Field(alias="job_description")
    summary: Optional[str] = Field(alias="job_summary")

    validate_last_updated = field_validator("last_updated", mode="before")(
        parse_datetime
    )

    @field_validator("min_salary", mode="before")  # noqa
    @classmethod
    def validate_min_salary(cls, value: Union[Decimal, str]) -> Decimal:
        """Ensure that the salary is in the correct format."""
        if isinstance(value, str):
            return Decimal(value)
        return value

    @field_validator("max_salary", mode="before")  # noqa
    @classmethod
    def validate_max_salary(cls, value: Union[str, Decimal]) -> Decimal:
        """Ensure that the salary is in the correct format."""
        if isinstance(value, str):
            return Decimal(value)
        return value

    @field_validator("last_updated", mode="before")
    def validate_last_updated(cls, value: Union[str, datetime]) -> datetime:
        """Ensure that last_updated is in the correct format."""
        return parse_datetime(value)


@register_model_transform
class IngestAggregatedStatistic(AggregatedStatisticSchema):
    pass
