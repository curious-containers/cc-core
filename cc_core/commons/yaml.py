import sys
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
yaml.default_flow_style = False


def load(stream):
    return yaml.load(stream)


def dump(stream, file_handle):
    yaml.dump(stream, file_handle)


def dump_print(stream, error=False):
    if error:
        yaml.dump(stream, sys.stderr)
    else:
        yaml.dump(stream, sys.stdout)
