from cc_core.commons.schemas.common import auth_schema

ccfaice_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'insecure': {'type': 'boolean'}
    },
    'additionalProperties': False
}

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
        'retryIfFailed': {'type': 'boolean'},
        'batchConcurrencyLimit': {'type': 'integer', 'minimum': 1}
        # disablePull might be data breach, if another users image has been pulled to host already
        # 'disablePull': {'type': 'boolean'}
    },
    'additionalProperties': False
}

execution_engines = {
    'ccfaice': ccfaice_schema,
    'ccagency': ccagency_schema
}
