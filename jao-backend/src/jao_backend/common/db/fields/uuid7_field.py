import os
import time
import uuid
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models


def uuidv7(hex: Optional[str] = None, timestamp: Optional[int] = None) -> uuid.UUID:
    """
    Generate a UUIDv7.

    (At the time of writing UUID7 is a standard but not included in Postgres until version 18)

    :param hex: Optional hex string to use as the UUID value.

    :return: A UUIDv7 object."""
    if hex is not None:
        return uuid.UUID(hex=hex)

    # random bytes
    value = bytearray(os.urandom(16))

    if timestamp is None:
        # current timestamp in ms
        timestamp = int(time.time() * 1000)

    # timestamp
    value[0] = (timestamp >> 40) & 0xFF
    value[1] = (timestamp >> 32) & 0xFF
    value[2] = (timestamp >> 24) & 0xFF
    value[3] = (timestamp >> 16) & 0xFF
    value[4] = (timestamp >> 8) & 0xFF
    value[5] = timestamp & 0xFF

    # version and variant
    value[6] = (value[6] & 0x0F) | 0x70
    value[8] = (value[8] & 0x3F) | 0x80

    return uuid.UUID(bytes=bytes(value))


class UUIDField(models.UUIDField):
    """
    A custom UUID field that generates different UUID versions.
    """

    # See: https://abenezer.org/blog/uuidv7-in-django

    def __init__(
        self,
        primary_key: bool = True,
        version: int | None = None,
        editable: bool = False,
        *args,
        **kwargs
    ):
        if version:
            if version == 2:
                raise ValidationError("UUID version 2 is not supported.")
            if version < 1 or version > 7:
                raise ValidationError("UUID version must be between 1 and 7.")

            version_map = {
                1: uuid.uuid1,
                3: uuid.uuid3,
                4: uuid.uuid4,
                5: uuid.uuid5,
                7: uuidv7,
            }
            kwargs.setdefault("default", version_map[version])
        else:
            kwargs.setdefault("default", uuid.uuid4)

        kwargs.setdefault("editable", editable)
        kwargs.setdefault("primary_key", primary_key)
        super().__init__(*args, **kwargs)
