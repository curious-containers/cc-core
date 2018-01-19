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
                'auth': auth_schema,
                'source': {
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
            'required': ['url']
        },
        'ram': {'type': 'integer', 'minimum': 256},
    },
    'additionalProperties': False,
    'required': ['image']
}

container_engines = {
    'docker': docker_schema
}
