from typing import Union
from django.db import models


def is_truthy(value: Union[str, bool]) -> bool:
    """
    Check whether a string represents a True boolean value.

    :param value: The value to check
    :type value: str or bool
    :rtype: bool
    """
    if not value:
        return False

    return str(value).lower() not in ("n", "no", "off", "f", "false", "0")

def is_concrete_model(cls):
    return issubclass(cls, models.Model) and not getattr(cls._meta, 'abstract', False)

def iter_concrete_subclass_models(cls, include=True):
    """Generator that yields non-abstract Model subclasses recursively."""
    if include and is_concrete_model(cls):
        yield cls

    for subclass in cls.__subclasses__():
        if is_concrete_model(subclass):
            yield subclass
        yield from iter_concrete_subclass_models(subclass, False)
