from jao_backend.common.db.models.models import ProtectedCharacteristicList


#  Protected Characteristics
class AgeGroup(ProtectedCharacteristicList):
    """Age groups JAO stores aggregated data about."""


class Disability(ProtectedCharacteristicList):
    """Disabilities JAO stores aggregated data about."""

    class Meta:
        verbose_name_plural = "Disabilities"


class EthnicGroup(ProtectedCharacteristicList):
    """Ethnic groups JAO stores aggregated data about."""


class Ethnicity(ProtectedCharacteristicList):
    """Ethnicities JAO stores aggregated data about."""

    class Meta:
        verbose_name_plural = "Ethnicities"


class Gender(ProtectedCharacteristicList):
    """Genders JAO stores aggregated data about."""


class Religion(ProtectedCharacteristicList):
    """Religions JAO stores aggregated data about."""


class SexualOrientation(ProtectedCharacteristicList):
    """Sexual orientations JAO stores aggregated data about."""
