from cc_core.commons.schemas.common import pattern_key
from cc_core.commons.schemas.cwl import cwl_schema
from cc_core.commons.engines import execution_engines, container_engines, virtualization_engines, source_engines
from cc_core.commons.engines import build_engines


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


inputs_schema = {
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


outputs_schema = {
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


faice_schema = {
    'type': 'object',
    'properties': {
        'version': {'enum': ['2']},
        'cwl': cwl_schema,
        'inputs': inputs_schema,
        'outputs': outputs_schema,
        'container': {
            'type': 'object',
            'properties': {
                'engine': {'enum': container_engines.keys()},
                'settings': {'type', 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'execution': {
            'type': 'object',
            'properties': {
                'engine': {'enum': execution_engines.keys()},
                'settings': {'type', 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'virtualization': {
            'type': 'object',
            'properties': {
                'engine': {'enum': virtualization_engines.keys()},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'source': {
            'type': 'object',
            'properties': {
                'engine': {'enum': source_engines.keys()},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        },
        'build': {
            'type': 'object',
            'properties': {
                'engine': {'enum': build_engines.keys()},
                'settings': {'type': 'object'}
            },
            'additionalProperties': False,
            'required': ['engine', 'settings']
        }
    },
    'additionalProperties': False,
    'required': ['version', 'cwl', 'inputs', 'outputs']
}
