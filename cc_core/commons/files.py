import os
import requests
import json
from urllib.parse import urlparse

from cc_core.commons.exceptions import AgentError

try:
    from ruamel.yaml import YAML
    yaml = YAML(typ='safe')
except:
    import ruamel.yaml as yaml


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
