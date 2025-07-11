import bbcode


def strip_bbcode(text):
    """Strip BBCode tags from text and return plain text"""
    parser = bbcode.Parser()
    return parser.strip(text)
