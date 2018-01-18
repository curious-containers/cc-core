bash_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'working_dir': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'path': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['path']
        },
        'script': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'path': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['path']
        }
    },
    'additionalProperties': False,
    'required': ['script']
}

build_engines = {
    'bash': bash_schema
}
