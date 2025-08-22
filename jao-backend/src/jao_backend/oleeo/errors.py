class DestinationModelError(ValueError):
    pass


class NoDestinationModel(DestinationModelError):
    pass


class DestinationModelNotFound(DestinationModelError):
    pass
