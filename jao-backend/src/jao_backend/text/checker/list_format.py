import re
from typing import Dict
from typing import Generator
from typing import Optional

from jao_backend.text.check import Check, Issue
from jao_backend.text.textspan import TextSpan


class ListFormatHybridChecker(Check):
    """
    Enhanced list format checker with:
    - Full item spans for context
    - Word-level highlights for precision
    - Consistent text grabbing
    """

    LIST_ITEM_PAT = re.compile(r"^\s*([-*])\s+(\S.*)$", re.MULTILINE)
    VALID_ENDINGS = (".", "!", "?")

    def check(self, span: TextSpan) -> Generator[Issue, None, None]:
        text = span.text
        seen_positions = set()

        for match in self.LIST_ITEM_PAT.finditer(text):
            if match.start() in seen_positions:
                continue
            seen_positions.add(match.start())

            item_span = span.slice(match.start(), match.end())
            first_char = match.group(2)[0] if match.group(2) else ""
            full_item = match.group(0).rstrip()

            # Capitalisation check
            if first_char and first_char.islower():
                # Grab bullet + first word for highlight
                first_word_end = match.start(2) + len(match.group(2).split()[0])
                highlight_span = span.slice(match.start(), first_word_end)

                yield self.new_issue(
                    span=item_span,  # Full item span
                    description="Capitalise first letter of list item",
                    highlight=[highlight_span],  # Bullet + first word
                )

            # Punctuation check
            if not full_item.endswith(self.VALID_ENDINGS):
                # Grab last word for highlight (or full item if short)
                last_word = (
                    full_item.split()[-1] if len(full_item.split()) > 1 else full_item
                )
                highlight_start = max(0, len(full_item) - len(last_word))

                yield self.new_issue(
                    span=item_span,  # Full item span
                    description="Add punctuation at end of list item",
                    highlight=[item_span.slice(highlight_start, None)],  # Last word
                )
