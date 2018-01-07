import os
from jsonschema import validate
from urllib.parse import urlparse
from traceback import format_exc
from glob import glob
from shutil import which

from cc_core.commons.exceptions import MissingInputFilesError, MissingOutputFilesError, InvalidBaseCommand
from cc_core.commons.schemas.cwl import cwl_schema, job_schema


def _assert_type(cwl_type, arg):
    if cwl_type == 'string':
        assert type(arg) == str
    elif cwl_type == 'integer' or cwl_type == 'long':
        assert type(arg) == int
    elif cwl_type == 'float' or cwl_type == 'double':
        assert type(arg) == float
    elif cwl_type == 'boolean':
        assert type(arg) == bool
    elif cwl_type == 'File':
        assert type(arg) == dict


def _location(arg):
    if arg.get('path'):
        return os.path.expanduser(arg['path'])

    p = arg['location']
    scheme = urlparse(p).scheme
    assert scheme == 'path'
    return os.path.expanduser(p[5:])


def _file_check(file_data, exception, error_text):
    missing_files = []
    for key, val in file_data.items():
        if val['size'] is None and not val['is_optional']:
            missing_files.append(key)
    if missing_files:
        raise exception(error_text.format(missing_files))


def cwl_input_file_check(input_files):
    _file_check(input_files, MissingInputFilesError, 'Missing input files: {}')


def cwl_output_file_check(output_files):
    _file_check(output_files, MissingOutputFilesError, 'Missing output files: {}')


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
            'is_optional': is_optional,
            'debug_info': None
        }

        if key in job_data:
            arg = job_data[key]
            try:
                file_path = _location(arg)
                file_path = os.path.expanduser(file_path)

                if input_dir and not os.path.isabs(file_path):
                    file_path = os.path.join(os.path.expanduser(input_dir), file_path)

                result['path'] = file_path
                assert os.path.exists(file_path)
                assert os.path.isfile(file_path)

                result['size'] = os.path.getsize(file_path) / (1024 * 1024)
            except:
                result['debug_info'] = format_exc()

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
            'is_optional': is_optional,
            'debug_info': None
        }

        glob_path = os.path.expanduser(val['outputBinding']['glob'])
        if output_dir and not os.path.isabs(glob_path):
            glob_path = os.path.join(os.path.expanduser(output_dir), glob_path)

        matches = glob(glob_path)
        try:
            assert len(matches) == 1
            file_path = matches[0]
            result['path'] = file_path

            assert os.path.exists(file_path)
            assert os.path.isfile(file_path)

            result['size'] = os.path.getsize(file_path) / (1024 * 1024)
        except:
            result['debug_info'] = format_exc()

        results[key] = result

    return results


def cwl_validation(cwl_data, job_data):
    validate(cwl_data, cwl_schema)
    validate(job_data, job_schema)

    for key, val in job_data.items():
        assert key in cwl_data['inputs']


def _check_base_command(base_command):
    if not which(base_command):
        raise InvalidBaseCommand('Invalid cwl base command: {}'.format(base_command))


def cwl_to_command(cwl_data, job_data, inputs_dir=None):
    base_command = cwl_data['baseCommand']
    _check_base_command(base_command)
    command = [base_command]
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
            assert val['inputBinding'].get('prefix') is not None

        try:
            arg = job_data[key]
        except KeyError as e:
            if is_optional:
                continue
            raise e

        if is_array:
            assert type(arg) == list
            assert len(arg) > 0

            for e in arg:
                _assert_type(cwl_type, e)
        else:
            _assert_type(cwl_type, arg)

        if cwl_type == 'File':
            file_path = _location(arg)
            file_path = os.path.expanduser(file_path)

            if inputs_dir and not os.path.isabs(file_path):
                file_path = os.path.join(inputs_dir, file_path)

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
            assert positional_arguments[pos] is None
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
