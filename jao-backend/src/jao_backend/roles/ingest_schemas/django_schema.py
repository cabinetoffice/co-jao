from pydantic import ConfigDict

from djantic import ModelSchema

from jao_backend.roles.models import Grade
from jao_backend.roles.models import RoleType


class GradeSchema(ModelSchema):
    model_config = ConfigDict(model=Grade, include=["id", "name", "last_updated"])  # type: ignore

class RoleTypeSchema(ModelSchema):
    model_config = ConfigDict(model=RoleType, include=["id", "description", "last_updated"])  # type: ignore
