import pytest

# from jao_backend.text.checkers import AcronymHybridChecker
from jao_backend.text.checker.acronym import AcronymHybridChecker
from jao_backend.text.textspan import TextSpan


@pytest.fixture
def sample_text():
    return "Sample text for testing"


class TestAcronymHybridCheckerUK:
    """Comprehensive test suite using GDPR and other UK-relevant examples"""

    @pytest.fixture
    def checker(sample_text):
        return AcronymHybridChecker(text=sample_text)
        # return AcronymHybridChecker(text=TextSpan.from_full_text(sample_text))

    def test_undefined_acronym_no_parentheses(self, checker):
        text = "GDPR compliance is important"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 1
        assert issues[0].description == "Undefined acronym: GDPR"
        assert issues[0].span.text == "GDPR"
        assert issues[0].span.start_index == 0
        assert issues[0].span.end_index == 4

    def test_undefined_acronym_with_parentheses(self, checker):
        text = "(GDPR) compliance is important"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        # THIS CURRENTLY FAILS - SHOULD DETECT (GDPR)
        assert len(issues) == 1
        assert issues[0].description == "Undefined acronym: GDPR"
        assert issues[0].span.text == "(GDPR)"
        assert issues[0].span.start_index == 0
        assert issues[0].span.end_index == 6

    def test_valid_parenthetical_definition(self, checker):
        text = "General Data Protection Regulation (GDPR) applies"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 0

    def test_usage_after_definition(self, checker):
        text = (
            "GDPR (General Data Protection Regulation) is important. Under GDPR,"
            " organizations must..."
        )
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 1
        # assert "used before definition" in issues[0].description

    def test_multiple_definitions(self, checker):
        text = (
            "GDPR (General Data Protection Regulation) and Privacy and Electronic"
            " Communications Regulations (PECR)"
        )
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 1

    def test_mixed_usage(self, checker):
        text = (
            "GDPR and PECR apply. General Data Protection Regulation (GDPR). Privacy"
            " and Electronic Communications Regulations (PECR)."
        )
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        # Should flag first occurrences before definition
        assert len(issues) == 2
        assert {i.description for i in issues} == {
            "Undefined acronym: GDPR",
            "Undefined acronym: PECR",
        }

    def test_multiline_definition(self, checker):
        text = "General Data Protection\nRegulation (GDPR) applies"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 0

    def test_punctuation_handling(self, checker):
        text = "The GDPR, or 'General Data Protection Regulation', applies"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 1
        assert issues[0].span.text == "GDPR"

    def test_uk_specific_acronyms(self, checker):
        text = "ICO (Information Commissioner's Office) handles GDPR breaches"
        doc = TextSpan.from_full_text(text)
        issues = list(checker.check(doc))

        assert len(issues) == 2

    def test_highlight_generation(self, checker):
        text = "GDPR compliance"
        doc = TextSpan.from_full_text(text)
        issue = next(checker.check(doc))

        assert issue.highlight[0].text == "GDPR"
