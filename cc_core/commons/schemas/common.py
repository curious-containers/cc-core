pattern_key = '^[a-zA-Z0-9_-]+$'

underscore_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'doc': {'type': 'string'},
            'template': {'type': 'string'},
            'disableProtection': {'type': 'boolean'}
        },
        'additionalProperties': False,
        'required': ['template']
    }, {
        'type': 'object',
        'properties': {
            'doc': {'type': 'string'},
            'value': {'type': 'string'},
            'disableProtection': {'type': 'boolean'}
        },
        'additionalProperties': False,
        'required': ['value']
    }]
}

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
            '_username': underscore_schema,
            'password': {'type': 'string'}
        },
        'addtionalProperties': False,
        'required': ['_username', 'password']
    }, {
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            '_password': underscore_schema
        },
        'addtionalProperties': False,
        'required': ['username', '_password']
    }, {
        'type': 'object',
        'properties': {
            '_username': underscore_schema,
            '_password': underscore_schema
        },
        'addtionalProperties': False,
        'required': ['_username', '_password']
    }]
}
