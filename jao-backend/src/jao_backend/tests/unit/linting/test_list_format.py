import pytest
from jao_backend.text.checker.list_format import ListFormatHybridChecker
from jao_backend.text.textspan import TextSpan


@pytest.mark.parametrize(
    "text,expected",
    [
        ("- Valid item.", []),
        ("- invalid item", ["Capitalise first letter"]),
        ("- item", ["Add punctuation"]),
        ("- ITEM", ["Add punctuation"]),
        ("- invalid item.", ["Capitalise first letter"]),
    ],
)
def test_list_format_linter(text, expected):
    span = TextSpan.from_full_text(text)
    checker = ListFormatHybridChecker(span)
    issues = list(checker.check(span))

    if not expected:
        assert not issues
    else:
        # Check that all expected issues are present (order doesnt matter)
        issue_descriptions = [i.description.lower() for i in issues]
        for expected_desc in expected:
            assert any(expected_desc.lower() in desc for desc in issue_descriptions)
