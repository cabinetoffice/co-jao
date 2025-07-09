from dataclasses import Field

from djantic import ModelSchema
from pydantic import ConfigDict

from jao_backend.roles.models import Grade
from jao_backend.roles.models import OleeoGradeGroup
from jao_backend.roles.models import OleeoRoleTypeGroup
from jao_backend.roles.models import RoleType


class OleeoGradeGroupSchema(ModelSchema):
    """
    Schema for OleeoGradeGroup model, which represents groups of job grades.
    """

    model_config = ConfigDict(model=OleeoGradeGroup, include=["id", "description", "shorthand", "last_updated"])  # type: ignoref


class OleeoRoleTypeSchema(ModelSchema):
    """
    Schema for OleeoRoleTypeGroup model, which represents groups of role types.
    """

    model_config = ConfigDict(model=OleeoRoleTypeGroup, include=["id", "description", "last_updated"])  # type: ignore


class RoleTypeSchema(ModelSchema):
    """Schema for RoleType.  Each row represent a single role type, exploded from OleeoRoleTypeGroup."""

    model_config = ConfigDict(
        model=RoleType,  # type: ignore
        include=["id", "description", "last_updated", "is_deleted"],
    )


class GradeSchema(ModelSchema):
    """Schema for Grade.  Each row represents a single grade, exploded from OleeoGradeGroup."""

    model_config = ConfigDict(
        model=Grade,  # type: ignore
        include=["id", "shorthand_name", "description", "last_updated"],
    )
