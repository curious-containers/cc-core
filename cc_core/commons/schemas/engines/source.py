from cc_core.commons.schemas.common import auth_schema


git_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'url': {'type': 'string'},
        'commit': {'type': 'string'},
        'auth': auth_schema
    },
    'additionalProperties': False,
    'required': ['url']
}

source_engines = {
    'git': git_schema
}
