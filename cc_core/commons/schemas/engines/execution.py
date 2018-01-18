from cc_core.commons.schemas.common import auth_schema


ccagency_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'enable_input_file_cache': {'type': 'boolean'},
        'url': {'type': 'string'},
        'auth': auth_schema
    },
    'additionalProperties': False
}

execution_engines = {
    'ccagency': ccagency_schema
}
