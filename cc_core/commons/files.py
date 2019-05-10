import os
import stat
import sys
import json
import requests
import textwrap
import shutil
from urllib.parse import urlparse
from ruamel.yaml import YAML

from cc_core.commons.exceptions import AgentError

JSON_INDENT = 4

yaml = YAML(typ='safe')
yaml.default_flow_style = False


WRITE_PERMISSIONS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


def move_files(output_files):
    for key, val in output_files.items():
        path = val['path']
        _, ext = os.path.splitext(path)
        file_name = ''.join([key, ext])
        try:
            shutil.move(path, file_name)
        except PermissionError:
            if os.path.exists(file_name):
                raise PermissionError('Cannot write output file "{}", because it already exists.\n'
                                      'You may have used an output directory that still contains read-only files?'
                                      .format(file_name))
            else:
                raise PermissionError('Cannot write output file "{}", because of insufficient permissions.\n'
                                      'Maybe check write permissions of the output directory.'.format(file_name))


def load_and_read(location, var_name):
    """
    Reads a path or URL and parses this file as yaml/json.
    :param location: The location as local path or URL
    :param var_name:
    :return:
    """
    if not location:
        return None
    raw_data = load(location, var_name)
    return read(raw_data, var_name)


def is_local(location):
    scheme = urlparse(location).scheme
    if scheme == 'http' or scheme == 'https':
        return False

    return True


def load(location, var_name):
    scheme = urlparse(location).scheme
    if scheme == 'path':
        return _local(location[5:], var_name)
    if scheme == '':
        return _local(location, var_name)
    if scheme == 'http' or scheme == 'https':
        return _http(location, var_name)

    raise AgentError('argument "{}" has unknown url scheme'.format(location))


def read(raw_data, var_name):
    try:
        data = yaml.load(raw_data)
    except:
        raise AgentError('data for argument "{}" is neither json nor yaml formatted.\ndata: {}'
                         .format(var_name, raw_data))

    if not isinstance(data, dict):
        raise AgentError('data for argument "{}" does not contain a dictionary.\ndata: "{}"'.format(var_name, data))

    return data


def file_extension(dump_format):
    if dump_format == 'json':
        return dump_format
    if dump_format in ['yaml', 'yml']:
        return 'yml'
    raise AgentError('invalid dump format "{}"'.format(dump_format))


def dump(stream, dump_format, file_name):
    if dump_format == 'json':
        with open(file_name, 'w') as f:
            json.dump(stream, f, indent=JSON_INDENT)
    elif dump_format in ['yaml', 'yml']:
        with open(file_name, 'w') as f:
            yaml.dump(stream, f)
    else:
        raise AgentError('invalid dump format "{}"'.format(dump_format))


def dump_print(stream, dump_format, error=False):
    if dump_format == 'json':
        if error:
            print(json.dumps(stream, indent=JSON_INDENT), file=sys.stderr)
        else:
            print(json.dumps(stream, indent=JSON_INDENT))
    elif dump_format in ['yaml', 'yml']:
        if error:
            yaml.dump(stream, sys.stderr)
        else:
            yaml.dump(stream, sys.stdout)
    elif dump_format != 'none':
        raise AgentError('invalid dump format "{}"'.format(dump_format))


def wrapped_print(blocks, error=False):
    if error:
        for block in blocks:
            print(textwrap.fill(block), file=sys.stderr)
    else:
        for block in blocks:
            print(textwrap.fill(block))


def _http(location, var_name):
    try:
        r = requests.get(location)
        r.raise_for_status()
    except:
        raise AgentError('file for argument "{}" could not be loaded via http'.format(var_name))
    return r.text


def _local(location, var_name):
    try:
        with open(os.path.expanduser(location)) as f:
            return f.read()
    except:
        raise AgentError('file for argument "{}" could not be loaded from file system'.format(var_name))


def for_each_file(base_dir, func):
    """
    Calls func(filename) for every file under base_dir.

    :param base_dir: A directory containing files
    :param func: The function to call with every file.
    """

    for dir_path, _, file_names in os.walk(base_dir):
        for filename in file_names:
            func(os.path.join(dir_path, filename))


def make_file_read_only(file_path):
    """
    Removes the write permissions for the given file for owner, groups and others.

    :param file_path: The file whose privileges are revoked.
    :raise FileNotFoundError: If the given file does not exist.
    """
    old_permissions = os.stat(file_path).st_mode
    os.chmod(file_path, old_permissions & ~WRITE_PERMISSIONS)
