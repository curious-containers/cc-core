from cc_core.commons.schemas.common import pattern_key
from cc_core.commons.schemas.cwl import cwl_schema
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines
from cc_core.commons.schemas.engines.virtualization import virtualization_engines


_connector_schema = {
    'type': 'object',
    'properties': {
        'py_module': {'type': 'string'},
        'py_class': {'type': 'string'},
        'access': {'type': 'object'}
    },
    'additionalProperties': False,
    'required': ['py_module', 'py_class', 'access']
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
    }
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
    }
}


red_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'format_version': {'enum': ['2']},
        'cwl': cwl_schema,
        'inputs': red_inputs_schema,
        'outputs': red_outputs_schema,
        'execution': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'enum': list(execution_engines.keys())},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'container': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'enum': list(container_engines.keys())},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'virtualization': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'engine': {'enum': list(virtualization_engines.keys())},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        }
    },
    'additionalProperties': False,
    'required': ['format_version', 'cwl', 'inputs', 'outputs']
}
