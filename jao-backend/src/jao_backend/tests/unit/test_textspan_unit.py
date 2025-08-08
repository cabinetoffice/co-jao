import unittest

from jao_backend.text.textspan import TextSpan


def test_text_span_merge():
    text = "The quick brown fox"
    span1 = TextSpan(text, 4, 9)  # "quick"
    span2 = TextSpan(text, 10, 15)  # "brown"
    merged = span1.merge(span2)

    assert merged.text == "quick brown"
    assert merged.start_index == 4
    assert merged.end_index == 15

def test_text_span_positioning():
    # Verify issue spans match source text positions
    span = TextSpan("Sample text", 7, 11)
    assert span.text == "text"
    assert span.start_index == 7
    assert span.end_index == 11
