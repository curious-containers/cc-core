vagrant_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'hypervisor': {'type': 'string'},
        'ram': {'type': 'integer', 'minimum': 256},
        'cpus': {'type': 'integer', 'minimum': 1},
        'os': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'image': {
                    'type': 'object',
                    'properties': {
                        'doc': {'type': 'string'},
                        'url': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['url']
                }
            },
            'additionalProperties': False,
            'required': 'image'
        }
    },
    'additionalProperties': False,
    'required': ['hypervisor', 'ram', 'os']
}

virtualization_engines = {
    'vagrant': vagrant_schema
}
