import bbcode


def strip_bbcode(text, parser=None):
    """
    Strip BBCode tags from text and return plain text

    :param text: The input text containing BBCode tags
    :param parser: Optional bbcode parser instance; if None, a new parser is created
    """
    if parser is None:
        parser = bbcode.Parser()
    return parser.strip(text)
