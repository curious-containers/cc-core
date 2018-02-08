from cc_core.commons.schemas.common import pattern_key
from cc_core.commons.schemas.cwl import cwl_schema

_connector_schema = {
    'type': 'object',
    'properties': {
        'pyModule': {'type': 'string'},
        'pyClass': {'type': 'string'},
        'access': {'type': 'object'}
    },
    'additionalProperties': False,
    'required': ['pyModule', 'pyClass', 'access']
}

# Reproducible Experiment Description (RED)
red_inputs_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {
                    'type': 'array',
                    'items': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'number'}
                        ]
                    }
                },
                {
                    'type': 'object',
                    'properties': {
                        'class': {'enum': ['File']},
                        'connector': _connector_schema
                    },
                    'additionalProperties': False,
                    'required': ['class', 'connector']
                }
            ]
        }
    },
    'additionalProperties': False
}


red_outputs_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {
            'type': 'object',
            'properties': {
                'class': {'enum': ['File']},
                'connector': _connector_schema
            },
            'additionalProperties': False,
            'required': ['class', 'connector']
        }
    },
    'additionalProperties': False
}


red_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'redVersion': {'type': 'string'},
        'cli': cwl_schema,
        'inputs': red_inputs_schema,
        'outputs': red_outputs_schema,
        'container': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'type': 'string'},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'execution': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'type': 'string'},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'virtualization': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'type': 'string'},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        }
    },
    'additionalProperties': False,
    'required': ['redVersion', 'cli', 'inputs']
}


red_jinja_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {'type': 'string'}
    },
    'additionalProperties': False
}
