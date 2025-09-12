"""
Pydantic schemas generated from Django models in jao_backend.application_statistics.models.

These schemas are one-to-one mappings of the Django models and should not be modified.

To add custom validation or additional fields create schema as a subclass in another module.
"""

from djantic import ModelSchema
from pydantic import ConfigDict

from jao_backend.application_statistics.models.lists import AgeGroup
from jao_backend.application_statistics.models.lists import Disability
from jao_backend.application_statistics.models.lists import EthnicGroup
from jao_backend.application_statistics.models.lists import Ethnicity
from jao_backend.application_statistics.models.lists import Gender
from jao_backend.application_statistics.models.lists import Religion
from jao_backend.application_statistics.models.lists import SexualOrientation


class AgeGroupSchema(ModelSchema):
    model_config = ConfigDict(model=AgeGroup, include=["id", "description", "last_updated"])  # type: ignore


class DisabilitySchema(ModelSchema):
    model_config = ConfigDict(model=Disability, include=["id", "description", "last_updated"])  # type: ignore


class EthnicGroupSchema(ModelSchema):
    model_config = ConfigDict(model=EthnicGroup, include=["id", "description", "last_updated"])  # type: ignore


class EthnicitySchema(ModelSchema):
    model_config = ConfigDict(model=Ethnicity, include=["id", "description", "last_updated"])  # type: ignore


class GenderSchema(ModelSchema):
    model_config = ConfigDict(model=Gender, include=["id", "description", "last_updated"])  # type: ignore


class ReligionSchema(ModelSchema):
    model_config = ConfigDict(model=Religion, include=["id", "description", "last_updated"])  # type: ignore


class SexualOrientationSchema(ModelSchema):
    model_config = ConfigDict(model=SexualOrientation, include=["id", "description", "last_updated"])  # type: ignore
