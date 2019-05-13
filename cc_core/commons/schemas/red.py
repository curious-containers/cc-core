from cc_core.commons.schemas.common import PATTERN_KEY
from cc_core.commons.schemas.cwl import _cwl_schema
from cc_core.commons.schema_transform import transform

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
        'connector': _connector_schema,
        'basename': {'type': 'string'},
        'dirname': {'type': 'string'},
        'checksum': {'type': 'string'},
        'size': {'type': 'integer'}
    },
    'additionalProperties': False,
    'required': ['class', 'connector']
}

_directory_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'connector': _connector_schema,
        'basename': {'type': 'string'},
        'listing': {'type': 'array'}
    },
    'additionalProperties': False,
    'required': ['class', 'connector']
}

_inputs_schema = {
    'type': 'object',
    'patternProperties': {
        PATTERN_KEY: {
            'anyOf': [
                {'type': 'null'},
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {
                    'type': 'array',
                    'items': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'number'},
                            {'type': 'boolean'},
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
        PATTERN_KEY: {
            'anyOf': [
                {
                    'type': 'object',
                    'properties': {
                        'class': {'enum': ['File']},
                        'connector': _connector_schema
                    },
                    'additionalProperties': False,
                    'required': ['class', 'connector']
                },
                {'type': 'null'}
            ]
        }
    },
    'additionalProperties': False
}

_engine_schema = {
    'type': 'object',
    'properties': {
        'engine': {'type': 'string'},
        'settings': {'type': 'object'}
    },
    'additionalProperties': False,
    'required': ['engine', 'settings']
}


# Reproducible Experiment Description (RED)
_red_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'redVersion': {'type': 'string'},
            'cli': _cwl_schema,
            'inputs': _inputs_schema,
            'outputs': _outputs_schema,
            'container': _engine_schema,
            'execution': _engine_schema
        },
        'additionalProperties': False,
        'required': ['redVersion', 'cli', 'inputs', 'container']
    }, {
        'type': 'object',
        'properties': {
            'redVersion': {'type': 'string'},
            'cli': _cwl_schema,
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
        'required': ['redVersion', 'cli', 'batches', 'container']
    }]
}

red_schema = transform(_red_schema)
