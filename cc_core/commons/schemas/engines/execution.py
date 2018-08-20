from cc_core.commons.schemas.common import auth_schema


ccagency_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'access': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'url': {'type': 'string'},
                'auth': auth_schema
            },
            'additionalProperties': False,
            'required': ['url']
        },
        'disablePull': {'type': 'boolean'},
        'outdir': {'type': 'string'},
        'protectedKeys': {
            'type': 'array',
            'items': {'type': 'string'}
        }
    },
    'additionalProperties': False
}

execution_engines = {
    'ccagency': ccagency_schema
}
