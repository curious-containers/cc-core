from copy import deepcopy

from cc_core.commons.exceptions import InvalidInputReference, ParsingError
from cc_core.commons.parsing import partition_all, split_into_parts

ATTRIBUTE_SEPARATOR_SYMBOLS = ['.', '["', '"]', '[\'', '\']']
INPUT_REFERENCE_START = '$('
INPUT_REFERENCE_END = ')'


def _get_dict_element(d, l):
    """
    Uses the keys in list l to get recursive values in d. Like return d[l[0]] [l[1]] [l[2]]...
    :param d: A dictionary
    :param l: A list of keys
    :return: The last value of d, after inserting all keys in l.
    """
    for e in l:
        d = d[e]
    return d


def create_inputs_to_reference(job_data, input_files, input_directories):
    """
    Creates a dictionary with the summarized information in job_data, input_files and input_directories

    :param job_data: The job data specifying input parameters other than files and directories.
    :param input_files: A dictionary describing the input files.
    :param input_directories: A dictionary describing the input directories.
    :return: A summarized dictionary containing information about all given inputs.
    """

    return {**deepcopy(job_data), **deepcopy(input_files), **deepcopy(input_directories)}


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


def resolve_input_reference(reference, inputs_to_reference):
    """
    Replaces a given input_reference by a string extracted from inputs_to_reference.

    :param reference: The input reference to resolve.
    :param inputs_to_reference: A dictionary containing information about the given inputs.

    :raise InvalidInputReference: If the given input reference could not be resolved.

    :return: A string which is the resolved input reference.
    """
    original_reference = reference
    if not reference.startswith('{}inputs.'.format(INPUT_REFERENCE_START)):
        raise InvalidInputReference('An input reference must have the following form '
                                    '"$(inputs.<input_name>[.<attribute>]".\n'
                                    'The invalid reference is: "{}"'.format(original_reference))
    # remove "$(" and ")"
    reference = reference[2:-1]
    parts = split_all(reference, ATTRIBUTE_SEPARATOR_SYMBOLS)

    if len(parts) < 2:
        raise InvalidInputReference('InputReference should at least contain "$(inputs.identifier)". The following '
                                    'input reference does not comply with it:\n{}'.format(original_reference))
    elif parts[0] != "inputs":
        raise InvalidInputReference('InputReference should at least contain "$(inputs.identifier)". The following '
                                    'input reference does not comply with it:\n{}'.format(original_reference))

    # remove 'inputs'
    parts = parts[1:]
    try:
        resolved = _get_dict_element(inputs_to_reference, parts)
    except KeyError as e:
        raise InvalidInputReference('Could not resolve input reference "{}". The key "{}" could not be resolved.'
                                    .format(original_reference, str(e)))
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
