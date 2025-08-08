from functools import lru_cache
import colorsys
from typing import Type

from collections.abc import Sequence
from html import escape

from IPython.core.display import HTML
from IPython.core.display_functions import display
from markdown_it import MarkdownIt

from recruitmentcopilot.text.check import Check, Issue


def generate_pastel_color(hue: float) -> str:
    """Generate a pastel color using HSL values."""
    r, g, b = colorsys.hsv_to_rgb(hue, 0.3, 1.0)  # Fixed low saturation (0.3) and full brightness (1.0)
    return f'rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})'

@lru_cache(maxsize=None)
def get_color_for_checker(checker: Type[Check]) -> str:
    """:return: A color in RGB format for the given class."""
    hue_number = int(hash(checker.__name__)) % 16_777_216

    hue = hue_number * 0.618033988749895  # Golden ratio to ensure good distribution
    hue = hue % 1.0
    color = generate_pastel_color(hue)
    return color


def issues_as_html(text: str, issues: Sequence[Issue]) -> str:
    """
    Output issues as HTML by inserting SPANs to describe the issues.
    """
    html_output = []
    last_end_index = 0
    tag = "span"

    for issue in issues:
        assert issue.span.source_text == text

        start_index = max(issue.span.start_index, last_end_index)
        end_index = issue.span.end_index

        # Assign a color to the checker class
        color = get_color_for_checker(issue.checker)

        # Append text before the issue
        if start_index > last_end_index:
            html_output.append(escape(text[last_end_index:start_index]))

        # Append the issue wrapped in a span with assigned color
        issue_text = escape(text[start_index:end_index])
        style = f'background-color: {color}; color: black'
        html_output.append(
            f'<{tag} class="text_issue text_issue_{issue.checker.__name__}" style="{style}" '
            f'title="{escape(issue.description)}">'
            f'{issue_text}</{tag}>')

        # Update the last_end_index
        last_end_index = end_index

    # Append the remaining text after the last issue
    html_output.append(escape(text[last_end_index:]))

    return ''.join(html_output)


def display_issues(text: str, issues: Sequence[Issue]) -> None:
    """
    Process the issues, generate the HTML output, and display it using IPython's display and HTML functions.
    """
    html_output = issues_as_html(text, issues)
    md = MarkdownIt()
    html = md.render(html_output)
    display(HTML(html))