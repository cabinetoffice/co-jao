"""
We carry our own small uuid7 implementation, based on
"""
import time
import uuid

from jao_backend.common.fields import uuidv7

def test_uuid7_from_hex():
    """
    Validate roundtrip from hex string to UUID7 and back
    """
    hex_string = "0196a4fe-4e54-77de-9ff1-e13291404e5a"
    value = uuidv7(hex=hex_string)

    assert isinstance(value, uuid.UUID)
    assert str(value) == hex_string

def test_uuid7_timestamp_ordering():
    """
    Validate that UUID7s are ordered by timestamp when passing in timestamps.
    """
    timestamp = int(time.time() * 1000)
    value1 = uuidv7().int
    value2 = uuidv7(timestamp=timestamp + 10).int

    assert value2 > value1
