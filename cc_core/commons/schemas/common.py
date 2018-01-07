pattern_key = '^[a-zA-Z0-9_-]+$'

auth_schema = {
    'type': 'object',
    'properties': {
        'username': {'type': 'string'},
        'password': {'type': 'string'}
    },
    'addtionalProperties': False,
    'required': ['username', 'password']
}
