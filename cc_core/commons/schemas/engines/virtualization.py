vagrant_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'hypervisor': {
            'type': 'object',
            'properties': {
                'engine': {'enum': ['virtualbox']},
                'settings': {
                    'type': 'object',
                    'properties': {
                        'version': {'type': 'string'}
                    },
                    'additionalProperties': False
                }
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'ram': {'type': 'integer', 'minimum': 256},
        'cpus': {'type': 'integer', 'minimum': 1}
    },
    'additionalProperties': False,
    'required': ['hypervisor', 'ram', 'cpus']
}
