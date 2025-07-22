import pytest
from jao_backend.text.textspan import TextSpan


@pytest.mark.parametrize(
    "source_text, start, end, expected_text",
    [
        ("Hello, world!", None, None, "Hello, world!"),
        ("Hello, world!", 7, 8, "w"),
        ("Hello, world!", 7, 12, "world"),
        ("Hello, world!", 15, 20, ""),
        ("Hello, world!", -6, -1, "world"),
        ("Hello, world!", None, 5, "Hello"),
        ("Hello, world!", -6, None, "world!"),
        ("Hello, world!", None, -1, "Hello, world"),
        ("Hello, world!", -1, None, "!"),
    ],
)
def test_textspan_slicing(source_text, start, end, expected_text):
    span = TextSpan.from_full_text(source_text)
    assert span[start:end].text == expected_text


@pytest.mark.parametrize(
    "source_text, index, expected_text",
    [
        ("Hello, world!", 7, "w"),
        ("Hello, world!", -1, "!"),
    ],
)
def test_textspan_indexing(source_text, index, expected_text):
    span = TextSpan.from_full_text(source_text)
    assert span[index].text == expected_text


def test_textspan_properties():
    source_text = "Hello, world!"
    span = TextSpan.from_full_text(source_text)

    assert len(span) == len(source_text)
    assert span.start_index == 0
    assert span.end_index == len(source_text)
    assert span.text == source_text
    assert repr(span) == f'<TextSpan (0, {len(source_text)}) "[{source_text}]">'


@pytest.mark.parametrize(
    "source_text, span1_indices, span2_indices, expected_equality",
    [
        ("Hello, world!", (None, None), (0, 13), True),
        ("Hello, world!", (7, 12), (7, 12), True),
        ("Hello, world!", (0, 5), (0, 4), False),
        ("Hello, world!", (None, None), (1, 12), False),
    ],
)
def test_textspan_equality(
    source_text, span1_indices, span2_indices, expected_equality
):
    span1 = TextSpan(source_text, *span1_indices)
    span2 = TextSpan(source_text, *span2_indices)
    assert (span1 == span2) == expected_equality


@pytest.mark.parametrize(
    "source_text, span_indices, comparison_string, expected_equality",
    [
        ("Hello, world!", (7, 12), "world", True),
        ("Hello, world!", (0, 5), "Hello", True),
        ("Hello, world!", (0, 5), "hello", False),
        ("Hello, world!", (None, None), "Hello, world!", True),
    ],
)
def test_textspan_string_equality(
    source_text, span_indices, comparison_string, expected_equality
):
    span = TextSpan(source_text, *span_indices)
    assert (span == comparison_string) == expected_equality


@pytest.mark.parametrize(
    "source_text, outer_span_indices, inner_span_indices, expected",
    [
        ("Hello, world!", (0, 13), (7, 12), True),  # "world" is within "Hello, world!"
        ("Hello, world!", (0, 5), (7, 12), False),  # "world" is not within "Hello"
        ("Hello, world!", (0, 13), (0, 13), True),  # Whole text span contains itself
        (
            "Hello, world!",
            (7, 12),
            (0, 13),
            False,
        ),  # "world" does not contain "Hello, world!"
    ],
)
def test_textspan_contains_textspan(
    source_text, outer_span_indices, inner_span_indices, expected
):
    outer_span = TextSpan(source_text, *outer_span_indices)
    inner_span = TextSpan(source_text, *inner_span_indices)
    assert (inner_span in outer_span) == expected


@pytest.mark.parametrize(
    "source_text, span_indices, substring, expected",
    [
        ("Hello, world!", (0, 13), "world", True),  # "world" is within "Hello, world!"
        ("Hello, world!", (0, 5), "world", False),  # "world" is not within "Hello"
        ("Hello, world!", (7, 12), "world", True),  # Exact match
        ("Hello, world!", (7, 12), "worl", True),  # Partial match
        ("Hello, world!", (7, 12), "Hello", False),  # "Hello" is not within "world"
    ],
)
def test_textspan_contains_string(source_text, span_indices, substring, expected):
    span = TextSpan(source_text, *span_indices)
    assert (substring in span) == expected
