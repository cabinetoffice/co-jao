from jao_backend.common.models import ListModel, ProtectedCharacteristicList


class RoleType(ListModel):
    """Role types JAO stores aggregated data about."""

class Grade(ProtectedCharacteristicList):
    """Job grades JAO stores aggregated data about."""
