from copy import deepcopy

from cc_core.commons.exceptions import InvalidInputReference

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
    parts = partition_all(to_split, [INPUT_REFERENCE_START, INPUT_REFERENCE_END])

    result = []
    part = []
    in_reference = False
    for p in parts:
        if in_reference:
            if p == INPUT_REFERENCE_START:
                raise InvalidInputReference('A new input reference has been started, although the old input reference'
                                            'has not yet been completed.\n{}'.format(to_split))
            elif p == ")":
                part.append(")")
                result.append(''.join(part))
                part = []
                in_reference = False
            else:
                part.append(p)
        else:
            if p == INPUT_REFERENCE_START:
                if part:
                    result.append(''.join(part))
                part = [INPUT_REFERENCE_START]
                in_reference = True
            else:
                part.append(p)

    if in_reference:
        raise InvalidInputReference('Input reference not closed.\n{}'.format(to_split))
    elif part:
        result.append(''.join(part))

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


def _resolve_file(attributes, input_file, input_identifier, input_reference):
    """
    Returns the attributes in demand of the input file.

    :param attributes: A list of attributes to get from the input_file.
    :param input_file: The file from which to get the attributes.
    :param input_identifier: The input identifier of the given file.
    :param input_reference: The reference string
    :return: The attribute in demand
    """
    if input_file['isArray']:
        raise InvalidInputReference('Input References to Arrays of input files are currently not supported.\n'
                                    '"{}" is an array of files and can not be resolved for input references:'
                                    '\n{}'.format(input_identifier, input_reference))
    single_file = input_file['files'][0]

    try:
        return _get_dict_element(single_file, attributes)
    except KeyError:
        raise InvalidInputReference('Could not get attributes "{}" from input file "{}", needed in input reference:'
                                    '\n{}'.format(attributes, input_identifier, input_reference))


def _resolve_directory(attributes, input_directory, input_identifier, input_reference):
    """
    Returns the attributes in demand of the input directory.

    :param attributes: A list of attributes to get from the input directory.
    :param input_directory: The directory from which to get the attributes.
    :param input_identifier: The input identifier of the given directory.
    :param input_reference: The reference string
    :return: The attribute in demand
    """
    if input_directory['isArray']:
        raise InvalidInputReference('Input References to Arrays of input directories are currently not supported.\n'
                                    'input directory "{}" is an array of directories and can not be resolved for input'
                                    'references:\n{}'.format(input_identifier, input_reference))
    single_directory = input_directory['directories'][0]

    try:
        return _get_dict_element(single_directory, attributes)
    except KeyError:
        raise InvalidInputReference('Could not get attributes "{}" from input directory "{}", needed in input'
                                    'reference:\n{}'.format(attributes, input_identifier, input_reference))


def resolve_input_reference(reference, inputs_to_reference):
    """
    Replaces a given input_reference by a string extracted from inputs_to_reference.

    :param reference: The input reference to resolve.
    :param inputs_to_reference: A dictionary containing information about the given inputs.

    :raise InvalidInputReference: If the given input reference could not be resolved.

    :return: A string which is the resolved input reference.
    """
    if not reference.startswith('{}inputs.'.format(INPUT_REFERENCE_START)):
        raise InvalidInputReference('An input reference must have the following form'
                                    '"$(inputs.<input_name>[.<attribute>]".\n'
                                    'The invalid reference is: "{}"'.format(reference))
    # remove "$(inputs." and ")"
    reference = reference[2:-1]
    parts = split_all(reference, ATTRIBUTE_SEPARATOR_SYMBOLS)

    if len(parts) < 2:
        raise InvalidInputReference('InputReference should at least contain "$(inputs.identifier)". The following input'
                                    'reference does not comply with it:\n{}'.format(reference))
    elif parts[0] != "inputs":
        raise InvalidInputReference('InputReference should at least contain "$(inputs.identifier)". The following input'
                                    ' reference does not comply with it:\n$({})'.format(reference))
    else:
        input_identifier = parts[1]
        input_to_reference = inputs_to_reference.get(input_identifier)
        if input_to_reference is None:
            raise InvalidInputReference('Input identifier "{}" not found in inputs, but needed in input reference:\n{}'
                                        .format(input_identifier, reference))
        elif isinstance(input_to_reference, dict):
            if 'files' in input_to_reference:
                return _resolve_file(parts[2:], input_to_reference, input_identifier, reference)
            elif 'directories' in input_to_reference:
                return _resolve_directory(parts[2:], input_to_reference, input_identifier, reference)
            else:
                raise InvalidInputReference('Unknown input type for input identifier "{}"'.format(input_identifier))
        else:
            if len(parts) > 2:
                raise InvalidInputReference('Attribute "{}" of input reference "{}" could not be resolved'
                                            .format(parts[2], reference))
            else:
                return parts[1]


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

    splitted = split_input_references(to_resolve)

    result = []

    for part in splitted:
        if is_input_reference(part):
            result.append(str(resolve_input_reference(part, inputs_to_reference)))
        else:
            result.append(part)

    return ''.join(result)
