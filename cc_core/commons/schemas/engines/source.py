from cc_core.commons.schemas.common import auth_schema


git_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'url': {'type': 'string'},
        'commit': {'type': 'string'},
        'auth': auth_schema
    },
    'additionalProperties': False,
    'required': ['url']
}
