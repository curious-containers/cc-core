from cc_core.commons.exceptions import InvalidInputReference, ParsingError
from cc_core.commons.parsing import partition_all, split_into_parts

ATTRIBUTE_SEPARATOR_SYMBOLS = ['.', '["', '"]', '[\'', '\']']
INDEX_SEPARATOR_SYMBOLS = ['[', ']']
INPUT_REFERENCE_START = '$('
INPUT_REFERENCE_END = ')'


def _resolve_keys_from_parts(inputs_to_reference, key_list):
    """
    Uses the keys in list key_list to get recursive values in inputs_to_reference.
    Like return inputs_to_reference[key_list[0]] [key_list[1]] ...

    :rtype: str
    :param inputs_to_reference: A recursive dictionary or list
    :param key_list: A list of keys to insert into the inputs to reference
    :return: The last value of d, after inserting all keys in key_list.
    """
    handled_keys = 'inputs'
    for key in key_list:
        if isinstance(inputs_to_reference, dict):
            if isinstance(key, str):
                inputs_to_reference = inputs_to_reference.get(key)
                if inputs_to_reference is None:
                    raise InvalidInputReference('Could not resolve "{}".'.format(key))
            else:
                raise InvalidInputReference(
                    'Could not resolve "{}" in "{}", because "{}" has type "{}". Expected type is "str".'
                    .format(key, handled_keys, key, type(key).__name__)
                )
        elif isinstance(inputs_to_reference, list):
            if isinstance(key, int):
                if key < len(inputs_to_reference):
                    inputs_to_reference = inputs_to_reference[key]
                else:
                    raise InvalidInputReference('Index {} is out of bounds in "{}", because "{}" has length {}.'
                                                .format(key, handled_keys, handled_keys, len(inputs_to_reference)))
            else:
                raise InvalidInputReference(
                    'Could not resolve "{}" in "{}", because "{}" is a list and the index "{}" ({}) is not given as int'
                    .format(key, handled_keys, handled_keys, key, type(key).__name__)
                )
        else:
            raise InvalidInputReference(
                'Could not resolve "{}", because type of "{}" is neither dict nor list'.format(key, handled_keys)
            )

        if isinstance(key, int):
            handled_keys = '{}[{}]'.format(handled_keys, key)
        else:
            handled_keys = '{}.{}'.format(handled_keys, key)

    if isinstance(inputs_to_reference, dict):
        raise InvalidInputReference(
            '"{}" could not be resolved completely. It is a dict, with the following keys: {}'
            .format(handled_keys, list(inputs_to_reference.keys()))
        )
    if isinstance(inputs_to_reference, list):
        raise InvalidInputReference(
            '"{}" could not be resolved completely. It is a list, with length {}'
            .format(handled_keys, len(inputs_to_reference))
        )

    return inputs_to_reference


def split_input_references(to_split):
    """
    Returns the given string in normal strings and unresolved input references.
    An input reference is identified as something of the following form $(...).

    Example:
    split_input_reference("a$(b)cde()$(fg)") == ["a", "$(b)", "cde()", "$(fg)"]

    :param to_split: The string to split
    :raise InvalidInputReference: If an input reference is not closed and a new reference starts or the string ends.
    :return: A list of normal strings and unresolved input references.
    """
    try:
        result = split_into_parts(to_split, INPUT_REFERENCE_START, INPUT_REFERENCE_END)
    except ParsingError as e:
        raise InvalidInputReference('Could not parse input reference "{}". Failed with the following message:\n{}'
                                    .format(to_split, repr(e)))
    return result


def is_input_reference(s):
    """
    Returns True, if s is an input reference.

    :param s: The string to check if it starts with INPUT_REFERENCE_START and ends with INPUT_REFERENCE_END.
    :return: True, if s is an input reference otherwise False
    """
    return s.startswith(INPUT_REFERENCE_START) and s.endswith(INPUT_REFERENCE_END)


def split_all(reference, sep):
    """
    Splits a given string at a given separator or list of separators.

    :param reference: The reference to split.
    :param sep: Separator string or list of separator strings.
    :return: A list of split strings
    """
    parts = partition_all(reference, sep)
    return [p for p in parts if p not in sep]


def _try_to_int(s):
    try:
        return int(s)
    except ValueError:
        return s


def _create_array_indices(parts):
    """
    Iterates over parts and tries to split array indices.
    :param parts: The parts that whose indices should be split.
    :return: A new list of parts, with extra elements defining the indices.
    """

    new_parts = []
    for part in parts:
        split_part = split_all(part, INDEX_SEPARATOR_SYMBOLS)
        if len(split_part) == 1:
            new_parts.append(split_part[0])
        elif len(split_part) > 1:
            new_parts.append(split_part[0])
            new_parts.extend([_try_to_int(p) for p in split_part[1:]])
        else:
            raise InvalidInputReference('Could not create array indices. {} is invalid.'.format(parts))

    return new_parts


def resolve_input_reference(reference, inputs_to_reference):
    """
    Replaces a given input_reference by a string extracted from inputs_to_reference.

    :param reference: The input reference to resolve.
    :param inputs_to_reference: A dictionary containing information about the given inputs.

    :raise InvalidInputReference: If the given input reference could not be resolved.

    :return: A string which is the resolved input reference.
    """
    original_reference = reference

    # remove "$(" and ")"
    reference = reference[2:-1]
    parts = split_all(reference, ATTRIBUTE_SEPARATOR_SYMBOLS)

    if len(parts) < 2:
        raise InvalidInputReference('InputReference should at least contain "$(inputs.<identifier>)". The following '
                                    'input reference does not comply with it:\n{}'.format(original_reference))
    elif parts[0] != "inputs":
        raise InvalidInputReference('InputReference should begin with "inputs". The following input reference does not '
                                    'comply with it:\n{}'.format(original_reference))

    # remove 'inputs'
    parts = parts[1:]

    parts = _create_array_indices(parts)

    try:
        resolved = _resolve_keys_from_parts(inputs_to_reference, parts)
    except InvalidInputReference as e:
        raise InvalidInputReference('Could not resolve input reference "{}".\n{}'.format(original_reference, str(e)))

    return resolved


def resolve_input_references(to_resolve, inputs_to_reference):
    """
    Resolves input references given in the string to_resolve by using the inputs_to_reference.

    See http://www.commonwl.org/user_guide/06-params/index.html for more information.

    Example:
    "$(inputs.my_file.nameroot).md" -> "filename.md"

    :param to_resolve: The path to match
    :param inputs_to_reference: Inputs which are used to resolve input references like $(inputs.my_input_file.basename).

    :return: A string in which the input references are replaced with actual values.
    """

    split_references = split_input_references(to_resolve)

    result = []

    for part in split_references:
        if is_input_reference(part):
            resolved = resolve_input_reference(part, inputs_to_reference)
            result.append(str(resolved))
        else:
            result.append(part)

    return ''.join(result)
