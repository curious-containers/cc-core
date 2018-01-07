from cc_core.commons.schemas.common import auth_schema


docker_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'image': {
            'type': 'object',
            'properties': {
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
