from copy import deepcopy


_HTTP_METHODS = ['Get', 'Put', 'Post']
_HTTP_METHODS_ENUMS = deepcopy(_HTTP_METHODS) + [m.lower() for m in _HTTP_METHODS] + [m.upper() for m in _HTTP_METHODS]

_AUTH_METHODS = ['Basic', 'Digest']
_AUTH_METHODS_ENUMS = deepcopy(_AUTH_METHODS) + [m.lower() for m in _AUTH_METHODS] + [m.upper() for m in _AUTH_METHODS]


http_schema = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'method': {'enum': _HTTP_METHODS_ENUMS},
        'auth': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string'},
                'password': {'type': 'string'},
                'method': {'enum': _AUTH_METHODS_ENUMS}
            },
            'additionalProperties': False,
            'required': ['username', 'password']
        },
        'ssl_verify': {'type': 'boolean'},
    },
    'additionalProperties': False,
    'required': ['url', 'method']
}

http_json_send_schema = deepcopy(http_schema)
http_json_send_schema['properties']['merge_agency_data'] = {'type': 'boolean'}
