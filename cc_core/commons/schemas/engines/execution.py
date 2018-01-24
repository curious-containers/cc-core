from cc_core.commons.schemas.common import auth_schema


ccagency_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
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
        'disableImagePull': {'type': 'boolean'},
        'enableInputCache': {'type': 'boolean'}
    },
    'additionalProperties': False
}

ccfaice_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'disableImagePull': {'type': 'boolean'},
    },
    'additionalProperties': False
}

cwltool_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'}
    },
    'additionalProperties': False
}

execution_engines = {
    'ccagency': ccagency_schema,
    'ccfaice': ccfaice_schema,
    'cwltool': cwltool_schema
}
