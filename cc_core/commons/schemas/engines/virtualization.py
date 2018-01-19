vagrant_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'ram': {'type': 'integer', 'minimum': 256},
        'cpus': {'type': 'integer', 'minimum': 1}
    },
    'additionalProperties': False,
    'required': ['ram']
}

virtualization_engines = {
    'vagrant': vagrant_schema
}
