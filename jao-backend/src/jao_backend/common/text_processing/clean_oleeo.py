import bbcode
import re

from jao_backend.common.text_processing.clean_bbcode import strip_bbcode


def oleeo_to_bbcode(text, strip_paragraphs=True):
    """
    Convert Oleeo-style BBCode lists to standard BBCode format.

    Converts [list=ul][li]...[/li][/list] to [list][*]...[/list]
    """
    # Replace [list=ul] with [list]
    text = re.sub(r"\[list=ul\]", "[list]", text, flags=re.IGNORECASE)

    # Replace [li]content[/li] with [*]content
    text = re.sub(
        r"\[li\](.*?)\[/li\]", r"[*]\1", text, flags=re.IGNORECASE | re.DOTALL
    )

    # Clean up any remaining [li] or [/li] tags
    text = re.sub(r"\[/?li\]", "", text, flags=re.IGNORECASE)

    if strip_paragraphs:
        text = re.sub(r"\[/?p\]", "", text, flags=re.IGNORECASE)

    return text


def get_oleeo_bbcode_parser():
    parser = bbcode.Parser()
    parser.add_simple_formatter("br", "<br>")
    parser.add_simple_formatter("p", "<p>%(value)s</p>")
    parser.add_simple_formatter("list", "<ul>%(value)s</ul>")
    parser.add_simple_formatter("*", "<li>%(value)s</li>")
    return parser


def strip_oleeo_bbcode(text):
    parser = get_oleeo_bbcode_parser()
    return strip_bbcode(text, parser=parser)


def parse_oleeo_bbcode(text):
    parser = get_oleeo_bbcode_parser()
    text = oleeo_to_bbcode(text, strip_paragraphs=False)
    return parser.format(text).strip()
