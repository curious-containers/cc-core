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
        'disableImagePull': {'type': 'boolean'},
        'enableInputCache': {'type': 'boolean'}
    },
    'additionalProperties': False
}

cc_faice_agent_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'disableImagePull': {'type': 'boolean'},
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
    'cc-agency': cc_agency_schema,
    'cc-faice-agent': cc_faice_agent_schema,
    'cwl-tool': cwl_tool_schema
}
