import sys

try:
    from ruamel.yaml import YAML
    yaml = YAML(typ='safe')

    def load(stream):
        return yaml.load(stream)

    def dump(stream, file_handle):
        yaml.dump(stream, file_handle)

    def dump_print(stream, error=False):
        if error:
            yaml.dump(stream, sys.stderr)
        else:
            yaml.dump(stream, sys.stdout)
except:
    # fallback for ruamel.yaml<0.15
    import ruamel.yaml as yaml
    from ruamel.yaml import Loader

    def load(stream):
        return yaml.load(stream, Loader=Loader)


    def dump(stream, file_handle):
        yaml.dump(stream, file_handle)


    def dump_print(stream, error=False):
        if error:
            print(yaml.dump(stream).rstrip(), file=sys.stderr)
        else:
            print(yaml.dump(stream).rstrip())
