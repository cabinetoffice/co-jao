"""
Immutable text reference implementation (ADR-006 compliant)
Allows safe slicing without modifying source text
"""

import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

from pydantic import Field


def _parse_match(match: re.Match) -> Tuple[int, int]:
    """
    Helper for TextSpan constructor to get indices from a regex match.

    :param match: A regex match object.
    :return: A tuple containing the start and end indices.
    """
    return match.span()


def _parse_indicies(
    start_index: Optional[int] = None, end_index: Optional[int] = None
) -> Tuple[Optional[int], Optional[int]]:
    """
    Helper for TextSpan constructor to get start and end indices.

    :param start_index: The start index of the span.
    :param end_index: The end index of the span.
    :return: A tuple containing the start and end indices.
    """
    return start_index, end_index


@dataclass(frozen=True)
class TextSpan:
    """
    Immutable text span with strict validation and document context.

    Key Features:
    - Guaranteed immutability
    - Safe initialization with bounds checking
    - Full document context preservation
    - Flexible slicing and merging
    - Consistent dict output for serialization

    Important: Changing the length of the source string is not supported.

    :param source_text: The source text.
    :param start: Absolute starting index (inclusive)
    :param end: Absolute ending index (exclusive)
    :param args: Positional arguments for start and end indices or a regex match.
    :param kwargs: Keyword arguments for start and end indices or a regex match.

    **Examples**:

    Create a TextSpan for the entire text:

    >>> span = TextSpan("Hello, world!")
    >>> span.text
    'Hello, world!'

    Create a TextSpan using start and end indices:

    >>> span = TextSpan("Hello, world!", 7, 12)
    >>> span.text
    'world'

    Create a TextSpan using a regex match:

    >>> import re
    >>> pattern = re.compile(r'world')
    >>> match = pattern.search("Hello, world!")
    >>> span = TextSpan("Hello, world!", match=match)
    >>> span.text
    'world'
    """

    source_text: str
    start_index: int = 0
    end_index: int = field(default=None)

    def __post_init__(self):

        # Handle None values
        if self.end_index is None:
            object.__setattr__(self, "end_index", len(self.source_text))
        if self.start_index is None:
            object.__setattr__(self, "start_index", 0)

        # Convert negative indices
        if self.start_index < 0:
            object.__setattr__(
                self, "start_index", max(0, len(self.source_text) + self.start_index)
            )
        if self.end_index < 0:
            object.__setattr__(
                self, "end_index", max(len(0, self.source_text) + self.end_index)
            )

        # Validate types and bounds
        if not 0 <= self.start_index <= self.end_index <= len(self.source_text):
            raise ValueError(f"Invalid span bounds {self.start_index}-{self.end_index}")

    @classmethod
    def from_full_text(cls, text: str) -> "TextSpan":
        """Factory method for spans covering entire text"""
        return cls(source_text=text, start_index=0, end_index=len(text))

    @classmethod
    def from_match(cls, source_text: str, match: re.Match) -> "TextSpan":
        """Factory from regex matches"""
        return cls(
            source_text=source_text, start_index=match.start(), end_index=match.end()
        )

    @property
    def text(self) -> str:
        """The referenced substring"""
        return self.source_text[self.start_index : self.end_index]

    @property
    def display_text(self) -> str:
        """Frontend-friendly text representation"""
        return self.text.replace("\u00a3", "£").replace(
            "\u20ac", "€"
        )  # For display purposes really..

    def to_dict(self) -> Dict[str, Any]:
        """Consistent serialization format for all spans"""
        return {
            "text": self.text,
            "display_text": self.display_text,
            "start": self.start_index,
            "end": self.end_index,
        }

    def slice(self, rel_start: int = 0, rel_end: Optional[int] = None) -> "TextSpan":
        """Create new span relative to current positions"""
        abs_start = self.start_index + rel_start
        abs_end = self.end_index if rel_end is None else self.start_index + rel_end
        return TextSpan(
            source_text=self.source_text, start_index=abs_start, end_index=abs_end
        )

    @classmethod
    def from_indices(
        cls, source_text: str, start_index: int = 0, end_index: Optional[int] = None
    ) -> "TextSpan":
        """
        Flexible index-based factory

        Args:
            end_index: If None, defaults to end of source_text
        """
        end = end_index if end_index is not None else len(source_text)
        return cls(
            source_text=source_text, start_index=start_index, end_index=end_index
        )

    def containing_document(self) -> "TextSpan":
        """Get span covering entire source text"""
        return TextSpan(self.source_text)

    def line_context(self, lines_before: int = 1, lines_after: int = 1) -> "TextSpan":
        """Expand span to include surrounding lines"""
        start = max(0, self.source_text.rfind("\n", 0, self.start_index, lines_before))
        end = self.source_text.find(
            "\n", self.end_index, self.end_index + lines_after * 100
        )
        end = end if end != -1 else len(self.source_text)
        return TextSpan(self.source_text, start, end)

    def highlight_context(self, context_chars: int = 20) -> Dict[str, Any]:
        """Return structured highlighting context"""

        return {
            "text": self.text,
            "context_pre": self.source_text[
                max(0, self.start_index - context_chars) : self.start_index
            ],
            "context_post": self.source_text[
                self.end_index : self.end_index + context_chars
            ],
            "absolute_pos": (self.start_index, self.end_index),
        }

    def merge(self, other: "TextSpan") -> "TextSpan":
        """Merge two spans from the same source"""

        if self.source_text != other.source_text:
            raise ValueError("Cannot merge spans from different source texts")
        return TextSpan(
            source_text=self.source_text,
            start_index=min(self.start_index, other.start_index),
            end_index=max(self.end_index, other.end_index),
        )

    @property
    def line_numbers(self) -> Tuple[int, int]:
        """Return (start_line, end_line) for the span"""

        start_line = self.source_text.count("\n", 0, self.start_index) + 1
        end_line = self.source_text.count("\n", 0, self.end_index) + 1
        return (start_line, end_line)

    def overlaps(self, other: "TextSpan") -> bool:
        """Check if spans overlap"""

        if self.source_text != other.source_text:
            return False
        return self.start_index < other.end_index and self.end_index > other.start_index

    def adjacent_to(self, other: "TextSpan") -> bool:
        """Check if spans are adjacent"""

        if self.source_text != other.source_text:
            return False
        return (
            self.end_index == other.start_index or other.end_index == self.start_index
        )

    def __bool__(self) -> bool:
        """
        :return: True if the span contains text, False otherwise.
        """
        return bool(self.text)

    def __eq__(self, other) -> bool:
        """
        :param other: Another TextSpan or a string.
        :return: True if the spans or span and string are equal.

        **Examples**:

        >>> span = TextSpan("Hello, world!", 7, 12)
        >>> span == "world"
        True
        >>> span == TextSpan("Hello, world!", 7, 12)
        True
        """
        if isinstance(other, TextSpan):
            return self.text == other.text
        elif isinstance(other, str):
            return self.text == other
        return NotImplemented

    def __len__(self) -> int:
        """
        :return: The length of the text within the span.
        """
        return self.end_index - self.start_index

    def __getitem__(self, key: Union[int, slice]) -> "TextSpan":
        """
        :param key: An index or slice.
        :return: A new TextSpan representing the sub-span.

        **Examples**:

        >>> span = TextSpan("Hello, world!")
        >>> span[7].text
        'w'
        >>> span[7:12].text
        'world'
        >>> span[15:20].text
        ''
        """
        if isinstance(key, int):
            if key < 0:
                key += len(self)
            if key < 0 or key >= len(self):
                raise IndexError("Index out of range")
            return TextSpan(
                self.source_text, self.start_index + key, self.start_index + key + 1
            )

        # Adjust the slice to the span's range
        start, stop, step = key.indices(len(self))
        new_start = self.start_index + start
        new_end = self.start_index + stop

        # Handle out-of-bounds slicing
        if new_start >= len(self.source_text) or new_end > len(self.source_text):
            return TextSpan(
                self.source_text, len(self.source_text), len(self.source_text)
            )

        return TextSpan(self.source_text, new_start, new_end)

    def __hash__(self):
        return hash(f"{self.start_index}:{self.end_index} {hash(self.source_text)}")

    def __contains__(self, other):
        """
        Check containment of substring or subspan

        Args:
            other: TextSpan or str to check for containment

        Returns:
            bool: True, if other is fully contained within this span
        Example:
            >>> span = TextSpan("Hello, world")
            >>> "ello" in span
            True
        """
        if isinstance(other, TextSpan):
            if self.source_text == other.source_text:
                return (
                    self.start_index <= other.start_index
                    and self.end_index >= other.end_index
                )
            return False

        elif isinstance(other, str):
            return other in self.text

        return False

    def __str__(self) -> str:
        """
        :return: The text within the span.
        """
        return self.text

    def __repr__(self):
        """
        :return: A string representation of the TextSpan
        """

        return f'<TextSpan ({self.start_index}, {self.end_index}) "[{self.text}]">'
