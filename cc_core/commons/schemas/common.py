pattern_key = '^[a-zA-Z0-9_-]+$'

auth_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'addtionalProperties': False,
        'required': ['username', 'password']
    }, {
        'type': 'object',
        'properties': {
            '_username': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'addtionalProperties': False,
        'required': ['_username', 'password']
    }, {
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            '_password': {'type': 'string'}
        },
        'addtionalProperties': False,
        'required': ['username', '_password']
    }, {
        'type': 'object',
        'properties': {
            '_username': {'type': 'string'},
            '_password': {'type': 'string'}
        },
        'addtionalProperties': False,
        'required': ['_username', '_password']
    }]
}
