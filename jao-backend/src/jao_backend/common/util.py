from typing import Union


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
