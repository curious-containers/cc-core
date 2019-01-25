import os
import jsonschema
from glob import glob
from jsonschema import ValidationError
from urllib.parse import urlparse
from shutil import which
from operator import itemgetter

from cc_core.commons.exceptions import exception_format
from cc_core.commons.exceptions import CWLSpecificationError, JobSpecificationError, FileError, DirectoryError
from cc_core.commons.input_references import resolve_input_references
from cc_core.commons.schemas.cwl import cwl_schema, cwl_job_schema, cwl_job_listing_schema, URL_SCHEME_IDENTIFIER

ARGUMENT_TYPE_MAPPING = {
    'string': str,
    'int': int,
    'long': int,
    'float': float,
    'double': float,
    'boolean': bool,
    'File': dict,
    'Directory': dict
}


def _assert_type(key, cwl_type, arg):
    pyt = ARGUMENT_TYPE_MAPPING.get(cwl_type)
    if pyt is None:
        raise CWLSpecificationError('argument "{}" has unknown type "{}"'.format(key, cwl_type))
    if not isinstance(arg, pyt):
        raise JobSpecificationError('"{}" argument "{}" has not been parsed to "{}"'.format(cwl_type, key, pyt))


def location(key, arg_item):
    if arg_item.get(URL_SCHEME_IDENTIFIER):
        return os.path.abspath(os.path.expanduser(arg_item[URL_SCHEME_IDENTIFIER]))

    p = arg_item['location']
    scheme = urlparse(p).scheme

    if scheme != 'file':
        raise JobSpecificationError('argument "{}" uses url scheme "{}" '
                                    'other than "{}"'.format(key, scheme, 'file'))

    return os.path.expanduser(p[5:])


def _arg_item_to_string(key, arg_item, input_dir):
    if isinstance(arg_item, dict):
        file_path = location(key, arg_item)

        if input_dir and not os.path.isabs(file_path):
            file_path = os.path.join(input_dir, file_path)

        return file_path

    return str(arg_item)


def _input_file_description(key, arg_item, input_dir):
    description = {
        'path': None,
        'size': None,
        'debugInfo': None,
        'nameroot': None,
        'nameext': None,
        'dirname': None
    }

    try:
        file_path = location(key, arg_item)

        if input_dir and not os.path.isabs(file_path):
            file_path = os.path.join(os.path.expanduser(input_dir), file_path)

        description['path'] = file_path
        if not os.path.exists(file_path):
            raise FileError('path does not exist')
        if not os.path.isfile(file_path):
            raise FileError('path is not a file')

        description['size'] = os.path.getsize(file_path) / (1024 * 1024)

        basename = os.path.basename(file_path)
        (nameroot, nameext) = os.path.splitext(basename)
        dirname = os.path.dirname(file_path)

        description['basename'] = basename
        description['nameroot'] = nameroot
        description['nameext'] = nameext
        description['dirname'] = dirname
    except:
        description['debugInfo'] = exception_format()

    return description


def _input_directory_description(input_identifier, arg_item, input_dir):
    """
     Produces a directory description. A directory description is a dictionary containing the following information.

     - 'path': An array containing the paths to the specified directories.
     - 'debugInfo': A field to possibly provide debug information.
     - 'found': A boolean that indicates, if the directory exists in the local filesystem.
     - 'listing': A listing that shows which files are in the given directory. This could be None.

    :param input_identifier: The input identifier in the cwl description file
    :param arg_item: The corresponding job information
    :param input_dir: TODO
    :return: A directory description
    :raise DirectoryError: If the given directory does not exist or is not a directory.
    """
    description = {
        'path': None,
        'found': False,
        'debugInfo': None,
        'listing': None,
        'basename': None
    }

    try:
        path = location(input_identifier, arg_item)

        if input_dir and not os.path.isabs(path):
            path = os.path.join(os.path.expanduser(input_dir), path)

        description['path'] = path
        if not os.path.exists(path):
            raise DirectoryError('path does not exist')
        if not os.path.isdir(path):
            raise DirectoryError('path is not a directory')

        description['listing'] = arg_item.get('listing')
        description['basename'] = os.path.basename(path)

        description['found'] = True
    except:
        description['debugInfo'] = exception_format()

    return description


def cwl_input_file_check(input_files):
    missing_files = []
    for key, val in input_files.items():
        if val['files'] is None:
            if not val['isOptional']:
                missing_files.append(key)
            continue

        for f in val['files']:
            if f['size'] is None:
                missing_files.append(key)
                continue

    if missing_files:
        raise FileError('missing input files {}'.format(missing_files))


def _check_input_directory_listing(base_directory, listing):
    """
    Raises an DirectoryError if files or directories, given in the listing, could not be found in the local filesystem.

    :param base_directory: The path to the directory to check
    :param listing: A listing given as dictionary
    :raise DirectoryError: If the given base directory does not contain all of the subdirectories and subfiles given in
    the listing.
    """

    for sub in listing:
        path = os.path.join(base_directory, sub['basename'])
        if sub['class'] == 'File':
            if not os.path.isfile(path):
                raise DirectoryError('File \'{}\' not found but specified in listing.'.format(path))
        if sub['class'] == 'Directory':
            if not os.path.isdir(path):
                raise DirectoryError('Directory \'{}\' not found but specified in listing'.format(path))
            sub_listing = sub.get('listing')
            if sub_listing:
                _check_input_directory_listing(path, sub_listing)


def cwl_input_directories_check(input_directories):
    missing_directories = []
    for key, val in input_directories.items():
        directories = val['directories']
        if directories is None and not val['isOptional']:
            missing_directories.append(key)
            continue

        for f in directories:
            if not f['found']:
                missing_directories.append(key)
                continue
            listing = f.get('listing')
            if listing:
                _check_input_directory_listing(f['path'], listing)

    if missing_directories:
        raise DirectoryError('missing input directories {}'.format(missing_directories))


def cwl_output_file_check(output_files):
    missing_files = []
    for key, val in output_files.items():
        if val['size'] is None and not val['isOptional']:
            missing_files.append(key)

    if missing_files:
        raise FileError('missing output files {}'.format(missing_files))


def cwl_output_directory_check(output_directories):
    missing_directories = []
    for key, val in output_directories.items():
        if not val['found'] and not val['isOptional']:
            missing_directories.append(key)

    if missing_directories:
        raise DirectoryError('missing output directories {}'.format(missing_directories))


def parse_cwl_type(cwl_type_string):
    """
    Parses cwl type information from a cwl type string.

    Examples:

    - "File[]" -> {'type': 'File', 'isArray': True, 'isOptional': False}
    - "int?" -> {'type': 'int', 'isArray': False, 'isOptional': True}

    :param cwl_type_string: The cwl type string to extract information from
    :return: A dictionary containing information about the parsed cwl type string
    """

    is_optional = cwl_type_string.endswith('?')
    if is_optional:
        cwl_type_string = cwl_type_string[:-1]

    is_array = cwl_type_string.endswith('[]')
    if is_array:
        cwl_type_string = cwl_type_string[:-2]

    return {'type': cwl_type_string, 'isArray': is_array, 'isOptional': is_optional}


def cwl_input_files(cwl_data, job_data, input_dir=None):
    results = {}

    for key, val in cwl_data['inputs'].items():
        cwl_type = parse_cwl_type(val['type'])

        (is_optional, is_array, cwl_type) = itemgetter('isOptional', 'isArray', 'type')(cwl_type)

        if cwl_type == 'File':
            result = {
                'isOptional': is_optional,
                'isArray': is_array,
                'files': None
            }

            if key in job_data:
                arg = job_data[key]

                if is_array:
                    result['files'] = [_input_file_description(key, i, input_dir) for i in arg]
                else:
                    result['files'] = [_input_file_description(key, arg, input_dir)]

            results[key] = result

    return results


def cwl_input_directories(cwl_data, job_data, input_dir=None):
    """
    Searches for Directories and in the cwl data and produces a dictionary containing input file information.

    :param cwl_data: The cwl data as dictionary
    :param job_data: The job data as dictionary
    :param input_dir: TODO
    :return: Returns the a dictionary containing information about input files.
             The keys of this dictionary are the input/output identifiers of the files specified in the cwl description.
             The corresponding value is a dictionary again with the following keys and values:
             - 'isOptional': A bool indicating whether this input directory is optional
             - 'isArray': A bool indicating whether this could be a list of directories
             - 'files': A list of input file descriptions

             A input file description is a dictionary containing the following information
             - 'path': The path to the specified directory
             - 'debugInfo': A field to possibly provide debug information
    """

    results = {}

    for input_identifier, input_data in cwl_data['inputs'].items():
        cwl_type = parse_cwl_type(input_data['type'])

        (is_optional, is_array, cwl_type) = itemgetter('isOptional', 'isArray', 'type')(cwl_type)

        if cwl_type == 'Directory':
            result = {
                'isOptional': is_optional,
                'isArray': is_array,
                'directories': None
            }

            if input_identifier in job_data:
                arg = job_data[input_identifier]

                if is_array:
                    result['directories'] = [_input_directory_description(input_identifier, i, input_dir) for i in arg]
                else:
                    result['directories'] = [_input_directory_description(input_identifier, arg, input_dir)]

            results[input_identifier] = result

    return results


def cwl_output_files(cwl_data, inputs_to_reference, output_dir=None):
    """
    Returns a dictionary containing information about the output files given in cwl_data.

    :param cwl_data: The cwl data from where to extract the output file information.
    :param inputs_to_reference: Inputs which are used to resolve input references.
    :param output_dir: Path to the directory where output files are expected.
    :return: A dictionary containing information about every output file.
    """
    results = {}

    for key, val in cwl_data['outputs'].items():
        cwl_type = parse_cwl_type(val['type'])
        (is_optional, is_array, cwl_type) = itemgetter('isOptional', 'isArray', 'type')(cwl_type)

        if not cwl_type == 'File':
            continue

        result = {
            'isOptional': is_optional,
            'path': None,
            'size': None,
            'debugInfo': None
        }

        glob_path = os.path.expanduser(val['outputBinding']['glob'])
        if output_dir and not os.path.isabs(glob_path):
            glob_path = os.path.join(os.path.expanduser(output_dir), glob_path)

        glob_path = resolve_input_references(glob_path, inputs_to_reference)
        matches = glob(glob_path)
        try:
            if len(matches) != 1:
                raise FileError('glob path "{}" does not match exactly one file'.format(glob_path))

            file_path = matches[0]
            result['path'] = file_path

            if not os.path.isfile(file_path):
                raise FileError('path is not a file')

            result['size'] = os.path.getsize(file_path) / (1024 * 1024)
        except:
            result['debugInfo'] = exception_format()

        results[key] = result

    return results


def cwl_output_directories(cwl_data, output_dir=None):
    results = {}

    for key, val in cwl_data['outputs'].items():
        cwl_type = parse_cwl_type(val['type'])
        (is_optional, is_array, cwl_type) = itemgetter('isOptional', 'isArray', 'type')(cwl_type)

        if not cwl_type == 'Directory':
            continue

        result = {
            'isOptional': is_optional,
            'path': None,
            'debugInfo': None,
            'found': False
        }

        glob_path = os.path.expanduser(val['outputBinding']['glob'])
        if output_dir and not os.path.isabs(glob_path):
            glob_path = os.path.join(os.path.expanduser(output_dir), glob_path)

        matches = glob(glob_path)
        try:
            if len(matches) != 1:
                raise DirectoryError('glob path "{}" does not match exactly one directory'.format(glob_path))

            file_path = matches[0]
            result['path'] = file_path

            if not os.path.isdir(file_path):
                raise DirectoryError('path is not a directory')

            result['found'] = True
        except:
            result['debugInfo'] = exception_format()

        results[key] = result

    return results


def cwl_validation(cwl_data, job_data, docker_requirement=False):
    try:
        jsonschema.validate(cwl_data, cwl_schema)
    except ValidationError as e:
        raise CWLSpecificationError('CWLFILE does not comply with jsonschema: {}'.format(e.context))

    try:
        jsonschema.validate(job_data, cwl_job_schema)
    except ValidationError as e:
        raise JobSpecificationError('JOBFILE does not comply with jsonschema: {}'.format(e.context))

    # validate listings
    for input_key, input_value in job_data.items():
        if isinstance(input_value, dict):
            listing = input_value.get('listing')
            if listing:
                try:
                    jsonschema.validate(listing, cwl_job_listing_schema)
                except ValidationError as e:
                    raise JobSpecificationError('listing of \'{}\' does not comply with jsonschema:\n{}'
                                                .format(input_key, e.context))

    for key, val in job_data.items():
        if key not in cwl_data['inputs']:
            raise JobSpecificationError('job argument "{}" is not specified in cwl'.format(key))

    if docker_requirement:
        if not cwl_data.get('requirements'):
            raise CWLSpecificationError('cwl does not contain DockerRequirement')

        if not cwl_data['requirements'].get('DockerRequirement'):
            raise CWLSpecificationError('DockerRequirement is missing in cwl')


def cwl_to_command(cwl_data, job_data, input_dir=None, check_executable=True):
    base_command = cwl_data['baseCommand']

    if isinstance(base_command, list):
        if len(base_command) < 1:
            raise CWLSpecificationError('invalid baseCommand "{}"'.format(base_command))

        executable = base_command[0].strip()
        subcommands = base_command[1:]
    else:
        executable = base_command.strip()
        subcommands = []

    if check_executable:
        if not which(executable):
            raise CWLSpecificationError('invalid executable "{}"'.format(executable))

    command = [executable] + subcommands
    prefixed_arguments = []
    positional_arguments = []

    for key, val in cwl_data['inputs'].items():
        cwl_type = val['type']

        is_optional = cwl_type.endswith('?')
        if is_optional:
            cwl_type = cwl_type[:-1]

        is_array = cwl_type.endswith('[]')
        if is_array:
            cwl_type = cwl_type[:-2]

        is_positional = val['inputBinding'].get('position') is not None

        if not is_positional:
            if not val['inputBinding'].get('prefix'):
                raise CWLSpecificationError('non-positional argument "{}" requires prefix'.format(key))

        if key not in job_data:
            if is_optional:
                continue
            raise JobSpecificationError('required argument "{}" is missing'.format(key))

        arg = job_data[key]

        if is_array:
            if not isinstance(arg, list):
                raise JobSpecificationError('array argument "{}" has not been parsed to list'.format(key))

            try:
                for e in arg:
                    _assert_type(key, cwl_type, e)
            except:
                raise JobSpecificationError(
                    '"{}" array argument "{}" contains elements of wrong type'.format(cwl_type, key)
                )
        else:
            _assert_type(key, cwl_type, arg)

        if is_array:
            if val['inputBinding'].get('prefix'):
                prefix = val['inputBinding'].get('prefix')

                if val['inputBinding'].get('separate', True):
                    arg = '{} {}'.format(prefix, ' '.join([_arg_item_to_string(key, i, input_dir) for i in arg]))

                elif val['inputBinding'].get('itemSeparator'):
                    item_sep = val['inputBinding']['itemSeparator']
                    arg = '{}{}'.format(prefix, item_sep.join([_arg_item_to_string(key, i, input_dir) for i in arg]))

                else:
                    arg = ' '.join(['{}{}'.format(prefix, _arg_item_to_string(key, i, input_dir)) for i in arg])

            else:
                item_sep = val['inputBinding'].get('itemSeparator')

                if not item_sep:
                    item_sep = ' '

                arg = item_sep.join([_arg_item_to_string(key, i, input_dir) for i in arg])

        elif val['inputBinding'].get('prefix'):
            prefix = val['inputBinding']['prefix']
            separate = val['inputBinding'].get('separate', True)

            if separate:
                if cwl_type == 'boolean':
                    if arg:
                        arg = prefix
                    else:
                        continue
                else:
                    arg = '{} {}'.format(prefix, _arg_item_to_string(key, arg, input_dir))
            else:
                arg = '{}{}'.format(prefix, _arg_item_to_string(key, arg, input_dir))

        if is_positional:
            pos = val['inputBinding']['position']
            additional = pos + 1 - len(positional_arguments)
            positional_arguments += [None for _ in range(additional)]
            if positional_arguments[pos] is not None:
                raise CWLSpecificationError('multiple positional arguments exist for position "{}"'.format(pos))
            positional_arguments[pos] = {'arg': _arg_item_to_string(key, arg, input_dir), 'is_array': is_array}
        else:
            prefixed_arguments.append(arg)

    positional_arguments = [p for p in positional_arguments if p is not None]

    first_array_index = len(positional_arguments)
    for i, p in enumerate(positional_arguments):
        if p['is_array']:
            first_array_index = i
            break
    front_positional_arguments = positional_arguments[:first_array_index]
    back_positional_arguments = positional_arguments[first_array_index:]

    command += [p['arg'] for p in front_positional_arguments]
    command += prefixed_arguments
    command += [p['arg'] for p in back_positional_arguments]

    return ' '.join([str(c) for c in command])
