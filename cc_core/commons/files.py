import os
import requests
import json
from ruamel.yaml import YAML
from urllib.parse import urlparse

from cc_core.commons.exceptions import FileFormatError, FileSchemeError


yaml = YAML(typ='safe')


def loads(s):
    try:
        return json.loads(s)
    except:
        try:
            return yaml.load(s)
        except:
            raise FileFormatError('Unsupported file format.')


def read_file(location):
    scheme = urlparse(location).scheme
    if scheme == 'path':
        return _local(location[5:])
    if scheme == '':
        return _local(location)
    if scheme == 'http' or scheme == 'https':
        return _http(location)
    raise FileSchemeError('Unsupported URL scheme.')


def _http(location):
    r = requests.get(location)
    r.raise_for_status()
    return r.text


def _local(location):
    with open(os.path.expanduser(location)) as f:
        return f.read()
