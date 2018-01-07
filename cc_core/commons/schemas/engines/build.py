docker_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'docker_file': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['path']
        }
    },
    'additionalProperties': False,
    'required': ['docker_file']
}
