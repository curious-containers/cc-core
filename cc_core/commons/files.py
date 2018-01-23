import os
import sys
import json
import requests
from urllib.parse import urlparse

import cc_core.commons.yaml as yaml
from cc_core.commons.exceptions import AgentError


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


def dump(stream, dump_format, file_name):
    if dump_format == 'json':
        with open(file_name, 'w') as f:
            return json.dump(stream, f, indent=4)
    if dump_format == 'yaml':
        with open(file_name, 'w') as f:
            return yaml.dump(stream, f)
    raise AgentError('unrecognized dump format "{}"'.format(dump_format))


def dumps(stream, dump_format):
    if dump_format == 'json':
        return json.dumps(stream, indent=4)
    if dump_format == 'yaml':
        return yaml.dumps(stream)
    raise AgentError('unrecognized dump format "{}"'.format(dump_format))


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
