from decimal import Decimal

from jao_backend.oleeo.ingest_schemas.oleeo_schema_registry import register_oleeo_mapping
from jao_backend.application_statistics.ingest_schemas.django_schema import AgeGroupSchema
from jao_backend.application_statistics.ingest_schemas.django_schema import DisabilitySchema
from jao_backend.application_statistics.ingest_schemas.django_schema import EthnicGroupSchema
from jao_backend.application_statistics.ingest_schemas.django_schema import EthnicitySchema
from jao_backend.application_statistics.ingest_schemas.django_schema import GenderSchema
from jao_backend.application_statistics.ingest_schemas.django_schema import ReligionSchema
from jao_backend.application_statistics.ingest_schemas.django_schema import SexualOrientationSchema
from jao_backend.roles.ingest_schemas.django_schema import GradeSchema
from jao_backend.roles.ingest_schemas.django_schema import RoleTypeSchema
from jao_backend.vacancies.ingest_schemas.django_schema import VacancySchema

from typing import Type, Optional, Any, Dict, Union
from pydantic import Field, ConfigDict, field_validator
from datetime import datetime


def validate_datetime(value: datetime) -> datetime:
    """Ensure that last_updated is in the correct format."""
    if isinstance(value, str):
        # Coerce to iso8601 format
        return datetime.fromisoformat(value)
    return value


def list_mixin_schema_factory(key_prefix: str = "") -> Type:
    """Factory that outputs a schema to:

    Rename fields by stripping a specified prefix from them.

    This is used to map the OLEEO tables which all have fields named with a table specific prefix,
    e.g. the List_AgeGroup has age_group_id, age_group_desc, these can be stripped.

    To use this factory, the source OLEEO table must have at least id, {prefix}_desc and row_last_updated
    columns.

    Factory function to create a ListSchemaMixin with the specified key_prefix.

    Args:
        key_prefix: The prefix to use for field aliases (e.g., "age_group_", "job_role_")

    Returns:
        A dynamically created mixin class with properly configured field aliases
    """

    def __str__(self) -> str:
        return self.description

    class_attrs: Dict[str, Any] = {
        "model_config": ConfigDict(populate_by_name=True),
        "id": Field(alias=f"{key_prefix}id"),
        "description": Field(alias=f"{key_prefix}desc"),
        "last_updated": Field(alias="row_last_updated"), "key_prefix": key_prefix,
        "validate_last_updated": field_validator("last_updated")(validate_datetime),
        "__doc__": "Dynamically generated mixin for list schema mappings",
        "__str__": __str__
    }

    return type(
        f"ListSchemaMixin{key_prefix.rstrip('_').title()}",
        (),
        class_attrs
    )


# Usage examples:
@register_oleeo_mapping
class IngestAgeGroups(list_mixin_schema_factory("age_group_"), AgeGroupSchema):
    """Map from OLEEO ListAgeGroup field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestDisabilities(list_mixin_schema_factory("disability_"), DisabilitySchema):
    """Map from OLEEO ListDisability field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestEthnicGroup(list_mixin_schema_factory("ethnic_group_"), EthnicGroupSchema):
    """Map from OLEEO ListEthnicGroup field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestEthnicity(list_mixin_schema_factory("ethnicity_"), EthnicitySchema):
    """Map from OLEEO ListEthnicity field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestGender(list_mixin_schema_factory("gender_"), GenderSchema):
    """Map from OLEEO ListGender field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestGrade(list_mixin_schema_factory("job_grade_"), GradeSchema):
    """Map from OLEEO ListJobGrade field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestReligion(list_mixin_schema_factory("religion_"), ReligionSchema):
    """Map from OLEEO ListReligion field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestRoleType(list_mixin_schema_factory("type_of_role_"), RoleTypeSchema):
    """Map from OLEEO ListRoleType field names to JAO names."""
    pass

@register_oleeo_mapping
class IngestSexualOrientation(list_mixin_schema_factory("sexual_orientation_"), SexualOrientationSchema):
    """Map from OLEEO ListSexualOrientation field names to JAO names."""
    pass


@register_oleeo_mapping
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

    validate_last_updated = field_validator("last_updated", mode="before")(validate_datetime)

    @field_validator("min_salary", mode="before")  # noqa
    @classmethod
    def validate_min_salary(cls, value: Union[Decimal, str]) -> Decimal:
        """Ensure that the salary is in the correct format."""
        if isinstance(value, str):
            # Coerce to decimal
            return Decimal(value.replace(",", ""))
        return value

    @field_validator("max_salary", mode="before")  # noqa
    @classmethod
    def validate_max_salary(cls, value: Union[str, Decimal]) -> Decimal:
        """Ensure that the salary is in the correct format."""
        if isinstance(value, str):
            # Coerce to decimal
            return Decimal(value)
        return value

    @field_validator("last_updated", mode="before")
    def validate_last_updated(cls, value: Union[str, datetime]) -> datetime:
        """Ensure that last_updated is in the correct format."""
        return validate_datetime(value)
