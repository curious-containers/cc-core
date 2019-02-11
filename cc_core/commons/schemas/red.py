import copy

from cc_core.commons.schemas.common import pattern_key
from cc_core.commons.schemas.cwl import cwl_schema

_connector_schema = {
    'type': 'object',
    'properties': {
        'command': {'type': 'string'},
        'access': {'type': 'object'},
        'mount': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': ['command', 'access']
}

_file_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'connector': _connector_schema
    },
    'additionalProperties': False,
    'required': ['class', 'connector']
}

_directory_schema = copy.deepcopy(_file_schema)
_directory_schema['properties']['class']['enum'] = ['Directory']
_directory_schema['properties']['listing'] = {'type': 'array'}

_inputs_schema = {
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
                            {'type': 'number'},
                            _file_schema,
                            _directory_schema
                        ]
                    }
                },
                _file_schema,
                _directory_schema
            ]
        }
    },
    'additionalProperties': False
}


_outputs_schema = {
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

_engine_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'engine': {'type': 'string'},
        'settings': {'type': 'object'}
    },
    'additionalProperties': False,
    'required': ['engine', 'settings']
}


# Reproducible Experiment Description (RED)
red_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'doc': {'type': 'string'},
            'redVersion': {'type': 'string'},
            'cli': cwl_schema,
            'inputs': _inputs_schema,
            'outputs': _outputs_schema,
            'container': _engine_schema,
            'execution': _engine_schema
        },
        'additionalProperties': False,
        'required': ['redVersion', 'cli', 'inputs']
    }, {
        'type': 'object',
        'properties': {
            'doc': {'type': 'string'},
            'redVersion': {'type': 'string'},
            'cli': cwl_schema,
            'batches': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'inputs': _inputs_schema,
                        'outputs': _outputs_schema
                    },
                    'additionalProperties': False,
                    'required': ['inputs']
                }
            },
            'container': _engine_schema,
            'execution': _engine_schema
        },
        'additionalProperties': False,
        'required': ['redVersion', 'cli', 'batches']
    }]
}


fill_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {'type': 'string'}
    },
    'additionalProperties': False
}
