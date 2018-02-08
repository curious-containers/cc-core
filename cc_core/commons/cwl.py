import os
import jsonschema
from urllib.parse import urlparse
from glob import glob
from shutil import which

from cc_core.commons.exceptions import exception_format
from cc_core.commons.exceptions import CWLSpecificationError, JobSpecificationError, FileError
from cc_core.commons.schemas.cwl import cwl_schema, cwl_job_schema


ARGUMENT_TYPE_MAPPING = (
    ('string', str),
    ('int', int),
    ('long', int),
    ('float', float),
    ('double', float),
    ('boolean', bool),
    ('File', dict)
)


def _assert_type(key, cwl_type, arg):
    for t, pyt in ARGUMENT_TYPE_MAPPING:
        if t == cwl_type:
            if isinstance(arg, pyt):
                return
            raise JobSpecificationError('"{}" argument "{}" has not been parsed to "{}"'.format(t, key, pyt))
    raise CWLSpecificationError('argument "{}" has unknown type "{}"'.format(key, cwl_type))


def location(key, arg):
    if arg.get('path'):
        return os.path.expanduser(arg['path'])

    p = arg['location']
    scheme = urlparse(p).scheme

    if scheme != 'path':
        raise JobSpecificationError('argument "{}" uses url scheme "{}" other than "path"'.format(key, scheme))

    return os.path.expanduser(p[5:])


def _file_check(file_data, error_text):
    missing_files = []
    for key, val in file_data.items():
        if val['size'] is None and not val['isOptional']:
            missing_files.append(key)
    if missing_files:
        raise FileError(error_text.format(missing_files))


def cwl_input_file_check(input_files):
    _file_check(input_files, 'missing input files {}')


def cwl_output_file_check(output_files):
    _file_check(output_files, 'missing output files {}')


def cwl_input_files(cwl_data, job_data, input_dir=None):
    results = {}

    for key, val in cwl_data['inputs'].items():
        cwl_type = val['type']
        is_optional = cwl_type.endswith('?')

        if is_optional:
            cwl_type = cwl_type[:-1]

        if not cwl_type == 'File':
            continue

        result = {
            'path': None,
            'size': None,
            'isOptional': is_optional,
            'debugInfo': None
        }

        if key in job_data:
            arg = job_data[key]
            try:
                file_path = location(key, arg)

                if input_dir and not os.path.isabs(file_path):
                    file_path = os.path.join(os.path.expanduser(input_dir), file_path)

                result['path'] = file_path
                if not os.path.exists(file_path):
                    raise FileError('path does not exist')
                if not os.path.isfile(file_path):
                    raise FileError('path is not a file')

                result['size'] = os.path.getsize(file_path) / (1024 * 1024)
            except:
                result['debugInfo'] = exception_format()

        results[key] = result

    return results


def cwl_output_files(cwl_data, output_dir=None):
    results = {}

    for key, val in cwl_data['outputs'].items():
        cwl_type = val['type']
        is_optional = cwl_type.endswith('?')

        if is_optional:
            cwl_type = cwl_type[:-1]

        if not cwl_type == 'File':
            continue

        result = {
            'path': None,
            'size': None,
            'isOptional': is_optional,
            'debugInfo': None
        }

        glob_path = os.path.expanduser(val['outputBinding']['glob'])
        if output_dir and not os.path.isabs(glob_path):
            glob_path = os.path.join(os.path.expanduser(output_dir), glob_path)

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


def cwl_validation(cwl_data, job_data, docker_requirement=False):
    try:
        jsonschema.validate(cwl_data, cwl_schema)
    except:
        raise CWLSpecificationError('cwl file does not comply with jsonschema')

    try:
        jsonschema.validate(job_data, cwl_job_schema)
    except:
        raise JobSpecificationError('job file does not comply with jsonschema')

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

    joined_subcommands = ' '.join([executable] + subcommands)

    command = [joined_subcommands]
    prefixed_arguments = []
    positional_arguments = []

    for key, val in cwl_data['inputs'].items():
        cwl_type = val['type']
        is_optional = cwl_type.endswith('?')
        is_array = cwl_type.endswith('[]')
        is_positional = val['inputBinding'].get('position') is not None

        if is_optional:
            cwl_type = cwl_type[:-1]
        elif is_array:
            cwl_type = cwl_type[:-2]

        if not is_positional:
            if not val['inputBinding'].get('prefix'):
                raise CWLSpecificationError('non-positional argument "{}" requires prefix'.format(key))

        if key not in job_data:
            if is_optional:
                continue
            raise JobSpecificationError('required argument "{}" is missing'.format(key))

        arg = job_data[key]

        if is_array:
            if (not isinstance(arg, list)) or len(arg) == 0:
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

        if cwl_type == 'File':
            file_path = location(key, arg)

            if input_dir and not os.path.isabs(file_path):
                file_path = os.path.join(input_dir, file_path)

            arg = file_path

        if is_array:
            if val['inputBinding'].get('prefix'):
                prefix = val['inputBinding'].get('prefix')

                if val['inputBinding'].get('separate', True):
                    arg = '{} {}'.format(prefix, ' '.join([str(e) for e in arg]))
                elif val['inputBinding'].get('itemSeparator'):
                    item_sep = val['inputBinding']['itemSeparator']
                    arg = '{}{}'.format(prefix, item_sep.join([str(e) for e in arg]))
                else:
                    arg = ' '.join(['{}{}'.format(prefix, e) for e in arg])
            else:
                item_sep = val['inputBinding'].get('itemSeparator')
                if not item_sep:
                    item_sep = ' '
                arg = item_sep.join([str(e) for e in arg])
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
                    arg = '{} {}'.format(prefix, arg)
            else:
                arg = '{}{}'.format(prefix, arg)

        if is_positional:
            pos = val['inputBinding']['position']
            additional = pos + 1 - len(positional_arguments)
            positional_arguments += [None for _ in range(additional)]
            if positional_arguments[pos] is not None:
                raise CWLSpecificationError('multiple positional arguments exist for position "{}"'.format(pos))
            positional_arguments[pos] = {'arg': arg, 'is_array': is_array}
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

    return ' '.join([str(e) for e in command])
