def get_first_named_span(match, *names):
    """
    Get the span of the first named group that is found in the match.

    :param match: The match object.
    :param names: The names of the groups to search for.
    :return: A tuple containing the start and end indices of the named group.
    :raises ValueError: If none of the names are found in the match group.
    """
    group_dict = match.groupdict()
    for name in names:
        value = group_dict.get(name)
        if value:
            start, end = match.span(name)
            return start, end
    raise ValueError(f"None of the names {names} found in the match group.")
