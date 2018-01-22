try:
    from ruamel.yaml import YAML
    yaml = YAML(typ='safe')

    def load(stream):
        return yaml.load(stream)
except:
    import ruamel.yaml as yaml
    from ruamel.yaml import Loader

    def load(stream):
        return yaml.load(stream, Loader=Loader)
