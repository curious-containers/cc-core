from cc_core.commons.schemas.common import auth_schema


docker_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'image': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'url': {'type': 'string'},
                'auth': auth_schema
            },
            'additionalProperties': False,
            'required': ['url']
        },
        'ram': {'type': 'integer', 'minimum': 256}
    },
    'additionalProperties': False,
    'required': ['image', 'ram']
}

container_engines = {
    'docker': docker_schema
}
