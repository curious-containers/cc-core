import os
import sys
import json
import requests
import textwrap
from urllib.parse import urlparse
from ruamel.yaml import YAML

from cc_core.commons.exceptions import AgentError

JSON_INDENT = 4

yaml = YAML(typ='safe')
yaml.default_flow_style = False


def load_and_read(location, var_name):
    if not location:
        return None
    raw_data = load(location, var_name)
    return read(raw_data, var_name)


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
        data = json.loads(raw_data)
    except:
        try:
            data = yaml.load(raw_data)
        except:
            raise AgentError('data for argument "{}" is neither json nor yaml formatted'.format(var_name))

    if not isinstance(data, dict):
        raise AgentError('data for argument "{}" does not contain a dictionary'.format(var_name))

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
    else:
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
