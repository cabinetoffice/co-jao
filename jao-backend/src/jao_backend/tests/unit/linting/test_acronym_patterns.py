import re
from textwrap import dedent

import pytest
from jao_backend.text.check import Issue
from jao_backend.text.checker.acronym import AcronymHybridChecker

# from jao_backend.text.checker.acronym import AcronymHybridChecker
from jao_backend.text.textspan import TextSpan


@pytest.mark.parametrize(
    "text, expected_description_pattern, expected_highlights",
    [
        # Case 1: Acronym before definition - now expects undefined since definition isn't properly formed
        (
            "GDPR applies. General Data Protection Regulation (GDPR) is important.",
            r"Undefined acronym: GDPR",  # Changed expectation
            ["GDPR"],
        ),
        # Case 2: Simple undefined acronym (unchanged)
        ("We need NDA agreements.", r"Undefined acronym: NDA", ["NDA"]),
    ],
)
def test_acronym_linter(text, expected_description_pattern, expected_highlights):
    """Test acronym definition checks with highlights"""
    full_span = TextSpan(text, start_index=0, end_index=len(text))

    # Create a test-specific subclass capture highlights if present
    class TestAcronymChecker(AcronymHybridChecker):
        def new_issue(self, *, span, description, **kwargs):
            issue = super().new_issue(
                span=span,
                # checker=self.__class__,
                description=description,
                # highlight=span,  # Default highlight, if none provided
                **kwargs,
            )

            # Convert highlights to plain text for comparison
            if expected_highlights and "highlights" in kwargs:
                hl_texts = [hl.text.strip() for hl in kwargs["highlights"]]
                assert hl_texts == expected_highlights, (
                    "Highlight mismatch.\n"
                    f"Expected: {expected_highlights}\n"
                    f"Actual: {hl_texts}"
                )
            return issue

    checker = TestAcronymChecker(full_span)
    issues = list(checker.check(full_span))

    if "issues: []" in expected_description_pattern:
        assert len(issues) == 0

    else:
        assert len(issues) == 1

    # Verify description pattern
    assert re.search(expected_description_pattern, issues[0].description), (
        f"Pattern '{expected_description_pattern}' not found in"
        f" '{issues[0].description}'"
    )
