from cc_core.commons.schemas.common import _auth_schema
from cc_core.commons.schema_transform import transform

_ccfaice_schema = {
    'type': 'object',
    'properties': {},
    'additionalProperties': False
}

_ccagency_schema = {
    'type': 'object',
    'properties': {
        'access': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'auth': _auth_schema
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

ccfaice_schema = transform(_ccfaice_schema)
ccagency_schema = transform(_ccagency_schema)

execution_engines = {
    'ccfaice': ccfaice_schema,
    'ccagency': ccagency_schema
}
