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
    return issubclass(cls, models.Model) and not getattr(cls._meta, "abstract", False)


def iter_concrete_subclass_models(cls, include=True):
    """Generator that yields non-abstract Model subclasses recursively."""
    if include and is_concrete_model(cls):
        yield cls

    for subclass in cls.__subclasses__():
        if is_concrete_model(subclass):
            yield subclass
        yield from iter_concrete_subclass_models(subclass, False)


def is_pk_numeric(model_class):
    """
    :return: True if the primary key field of the model supports numeric lookups.
    """
    pk_field = model_class._meta.pk

    # These lookups are only available on numeric fields
    numeric_lookups = {"gt", "gte", "lt", "lte"}
    available_lookups = set(pk_field.get_lookups().keys())

    return numeric_lookups.issubset(available_lookups)
