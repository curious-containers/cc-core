pattern_key = '^[a-zA-Z0-9_-]+$'

listing_sub_file_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'basename': {'type': 'string'},
    },
    'required': ['class', 'basename'],
    'additionalProperties': False
}

listing_sub_directory_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'basename': {'type': 'string'},
        'listing': {'$ref': '#/'}
    },
    'additionalProperties': False,
    'required': ['class', 'basename']
}

# WARNING: Do not embed this schema into another schema,
# because this will break the '$ref' in listing_sub_directory_schema
listing_schema = {
    'type': 'array',
    'items': {
        'oneOf': [listing_sub_file_schema, listing_sub_directory_schema]
    }
}

auth_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['username', 'password']
    }, {
        'type': 'object',
        'properties': {
            '_username': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['_username', 'password']
    }, {
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            '_password': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['username', '_password']
    }, {
        'type': 'object',
        'properties': {
            '_username': {'type': 'string'},
            '_password': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['_username', '_password']
    }]
}
