from cc_core.commons.exceptions import ParsingError


def _partition_all_internal(s, sep):
    """
    Uses str.partition() to split every occurrence of sep in s. The returned list does not contain empty strings.

    :param s: The string to split.
    :param sep: A separator string.
    :return: A list of parts split by sep
    """
    parts = list(s.partition(sep))

    # if sep found
    if parts[1] == sep:
        new_parts = partition_all(parts[2], sep)
        parts.pop()
        parts.extend(new_parts)
        return [p for p in parts if p]
    else:
        if parts[0]:
            return [parts[0]]
        else:
            return []


def partition_all(s, sep):
    """
    Uses str.partition() to split every occurrence of sep in s. The returned list does not contain empty strings.
    If sep is a list, all separators are evaluated.

    :param s: The string to split.
    :param sep: A separator string or a list of separator strings.
    :return: A list of parts split by sep
    """
    if isinstance(sep, list):
        parts = _partition_all_internal(s, sep[0])
        sep = sep[1:]

        for s in sep:
            tmp = []
            for p in parts:
                tmp.extend(_partition_all_internal(p, s))
            parts = tmp

        return parts
    else:
        return _partition_all_internal(s, sep)


def split_into_parts(to_split, start, end):
    """
    Returns the given string split in normal strings and framed strings, framed by <start> and <end>.
    An input reference is identified as something of the following form $(...).

    Example:
    split_into_parts("a(b)cde()(fg)", star='(', end=')') == ["a", "(b)", "cde", "()", "(fg)"]

    :param to_split: The string to split
    :param start: The start sequence to search for
    :param end: The end sequence to search for
    :raise ParsingError: If an input reference is not closed and a new reference starts or the string ends.
    :return: A list of normal strings and unresolved input references.
    """
    parts = partition_all(to_split, [start, end])

    result = []
    part = []
    in_reference = False
    for p in parts:
        if in_reference:
            if p == start:
                raise ParsingError('A new framed string has been started, although the old framed string has not yet '
                                   'been completed.\n{}'.format(to_split))
            elif p == end:
                part.append(end)
                result.append(''.join(part))
                part = []
                in_reference = False
            else:
                part.append(p)
        else:
            if p == start:
                if part:
                    result.append(''.join(part))
                part = [start]
                in_reference = True
            else:
                part.append(p)

    if in_reference:
        raise ParsingError('Framed string started but not closed.\n{}'.format(to_split))
    elif part:
        result.append(''.join(part))

    return result
