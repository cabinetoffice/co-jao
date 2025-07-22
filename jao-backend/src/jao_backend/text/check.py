"""Immutable issue reporting system"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from .textspan import TextSpan


@dataclass
class Issue:
    span: TextSpan
    """The span of text with the issue."""

    checker: Type["Check"]
    """Which checker class found the issue."""

    description: str
    """Human readable description, defaults to docstring of Checker class"""

    highlight: Optional[List[TextSpan]]
    """Spans of text to highlight, defaults to the span where the issue was found, but can include others."""

    def __post_init__(self):
        if self.highlight is None:
            self.highlight = [self.span]

    def to_dict(self) -> Dict[str, Any]:

        def clean_text(text: str) -> str:
            return text.replace("\u00a3", "£").replace("\u20ac", "€")

        return {
            "span": {
                "text": self.span.text,
                "display_text": clean_text(self.span.text),
                "start": self.span.start_index,
                "end": self.span.end_index,
            },
            "checker": self.checker.__name__,
            "description": self.description,
            "highlight": [
                {
                    "text": h.text,
                    "display_text": clean_text(h.text),
                    "start": h.start_index,
                    "end": h.end_index,
                }
                for h in self.highlight
            ],
        }

    # def __repr__(self):
    #     return f"Issue(checker={type(self).__name__}, description='{self.description}', highlight='{self.highlight}', span={self.span})"


class Check:
    description: str = ""

    _registry = {}

    def __init__(self, text: TextSpan):
        """
        :param text: Document to check for issues.

        Subclasses can pre-process the text here.
        """
        pass

    @classmethod
    def new_issue(
        cls,
        span: TextSpan,
        highlight: Optional[List[TextSpan]] = None,
        description: Optional[str] = None,
    ) -> Issue:

        if description is None:
            description = cls.__doc__
            if description is None:
                raise ValueError(
                    "No description supplied for issue and no docstring for"
                    f" {cls.__name__}"
                )

        return Issue(
            span=span, checker=cls, description=description, highlight=highlight
        )

    def check(self, span: TextSpan) -> Generator[Issue, None, None]:
        raise NotImplementedError(f"{type(self).__name__}.check() must be implemented.")
