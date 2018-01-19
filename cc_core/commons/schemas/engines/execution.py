from cc_core.commons.schemas.common import auth_schema


cc_agency_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
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
        'disable_image_pull': {'type': 'boolean'},
        'enable_input_cache': {'type': 'boolean'}
    },
    'additionalProperties': False
}

cc_faice_agent_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'disable_image_pull': {'type': 'boolean'},
    },
    'additionalProperties': False
}

cwl_tool_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'}
    },
    'additionalProperties': False
}

execution_engines = {
    'cc_agency': cc_agency_schema,
    'cc_faice_agent': cc_faice_agent_schema,
    'cwl_tool': cwl_tool_schema
}
