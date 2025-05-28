from enum import Enum
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Sequence
from typing import Tuple
from typing import Type

EnumMemberSequence = Iterator[Tuple[str, Any]]


class SerializableEnumMixin:
    @classmethod
    def as_sequence(cls: Type[Enum]) -> EnumMemberSequence:
        """
        :return: Generator of (name, value) tuples for each member of the Enum
        """
        return ((member.name, member.value) for member in cls)


def enums_as_dict(
    enum_classes: Sequence[Type[SerializableEnumMixin]],
) -> Dict[str, EnumMemberSequence]:
    """
    Given a list of Enums return a dictionary with the Enum class name as the
    key and the Enum members as the value
    """
    return {
        enum_class.__name__: enum_class.as_sequence() for enum_class in enum_classes
    }


def string_as_enum(enum_classes: Sequence[Type[Enum]], string_value: str) -> Enum:
    """
    Given a list of Enums return the Enum member that matches the string value
    or raise a ValueError if no match is found

    :param enum_classes: List of enum classes to search in
    :param string_value: String representation of the enum member
    :return: Enum member
    :raises ValueError: If no match is found
    """
    for enum_class in enum_classes:
        try:
            return enum_class[string_value]
        except KeyError:
            pass

    raise ValueError(f"{string_value} is not found in: {enum_classes}")
