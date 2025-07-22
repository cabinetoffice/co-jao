import re
from typing import Dict, Generator

from jao_backend.text.check import Check, Issue
from jao_backend.text.textspan import TextSpan


class AcronymHybridChecker(Check):
    """
    Hybrid checker for acronym definitions ensuring efficient pre-computation
    and real-time validation, with full span integration

    Stateless validation with pre-compiled and robust pattern matching
    """

    ACRONYM_PAT = re.compile(
        r"(?:\(([A-Z]{2,5})\)|([A-Z]{2,5})(?![)]))"
    )  # Captures both (ABC) and ABC
    DEFINITION_PAT = re.compile(
        r"((?:[A-Z][a-z]+(?:[\s][A-Z][a-z]+)+)[\s,:-]*\(([A-Z]{2,5})\))"  # Parenthetical, now allows newlines
        r"|"  # OR
        r"((?:[A-Z][a-z]+(?:[\s][A-Z][a-z]+)+)[\s,:-]+([A-Z]{2,5})\b)",  # Inline, also allows newlines
        re.MULTILINE,
    )

    def check(self, span: TextSpan) -> Generator[Issue, None, None]:
        doc = span.containing_document()
        definitions = self._find_definitions(doc)
        first_occurrences = {}

        # First pass: Find all acronym usages (excluding definitions)
        for match in self.ACRONYM_PAT.finditer(span.text):
            acronym = match.group(1) or match.group(2)
            abs_pos = span.start_index + match.start()

            # Skip if this is part of a definition match
            if self._is_definition_match(doc, match):
                continue

            if acronym not in first_occurrences:
                first_occurrences[acronym] = {
                    "span": span.slice(match.start(), match.end()),
                    "position": abs_pos,
                }

        # Second pass: Validate against definitions
        for acronym, data in first_occurrences.items():
            if acronym not in definitions:
                yield self.new_issue(
                    span=data["span"], description=f"Undefined acronym: {acronym}"
                )
            elif data["position"] < definitions[acronym].start_index:
                yield self.new_issue(
                    span=data["span"],
                    description=f"Acronym '{acronym}' used before definition",
                    highlights=[data["span"], definitions[acronym]],
                )

    def _find_definitions(self, doc: TextSpan) -> Dict[str, TextSpan]:
        definitions = {}
        for match in self.DEFINITION_PAT.finditer(doc.text):
            try:
                if match.group(2):  # Parenthetical case
                    term, acronym = match.group(1), match.group(2)

                else:  # Inline case
                    term, acronym = match.group(3), match.group(4)

                if self._is_valid_definition(term, acronym):
                    definitions[acronym] = TextSpan.from_match(doc.source_text, match)
            except (IndexError, ValueError):
                continue
        return definitions

    def _is_valid_definition(self, term: str, acronym: str) -> bool:
        term_initials = "".join([w[0].upper() for w in term.split()])
        return term_initials == acronym

    def _is_definition_match(self, doc: TextSpan, match: re.Match) -> bool:
        """Check if this match is part of a definition pattern"""
        for def_match in self.DEFINITION_PAT.finditer(doc.text):
            if def_match.start() <= match.start() <= def_match.end():
                return True
        return False
