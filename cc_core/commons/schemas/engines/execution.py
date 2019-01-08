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
        # disablePull might be data breach, if another users image has been pulled to host already
        # 'disablePull': {'type': 'boolean'}
    },
    'additionalProperties': False
}

execution_engines = {
    'ccagency': ccagency_schema
}
