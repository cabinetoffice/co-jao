def readable_pk_range(instances):
    """
    Return a readable string of the primary keys of the instances.
    """
    if not instances:
        return "[none]"

    if len(instances) == 1:
        return f"[{instances[0].pk}]"

    return f"[{instances[0].pk}-{instances[len(instances) - 1].pk}]"
