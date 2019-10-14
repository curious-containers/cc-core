from cc_core.commons.schemas.common import PATTERN_KEY
from cc_core.commons.schemas.cwl import cwl_schema
from cc_core.commons.schema_transform import transform

_connector_schema = {
    'type': 'object',
    'properties': {
        'command': {'type': 'string'},
        'access': {'type': 'object'},
        'mount': {'type': 'boolean'},
        'doc': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['command', 'access']
}

_input_file_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'connector': _connector_schema,
        'basename': {'type': 'string'},
        'dirname': {'type': 'string'},
        'checksum': {'type': 'string'},
        'size': {'type': 'integer'},
        'doc': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['class', 'connector']
}

_input_directory_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'connector': _connector_schema,
        'basename': {'type': 'string'},
        'listing': {'type': 'array'},
        'doc': {'type': 'string'}
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
                            _input_file_schema,
                            _input_directory_schema
                        ]
                    }
                },
                _input_file_schema,
                _input_directory_schema
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
                        'class': {'enum': ['File', 'stdout', 'stderr']},
                        'checksum': {'type': 'string'},
                        'size': {'type': 'integer'},
                        'connector': _connector_schema,
                        'doc': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['class', 'connector']
                }, {
                    'type': 'object',
                    'properties': {
                        'class': {'enum': ['Directory']},
                        'connector': _connector_schema,
                        'doc': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['class', 'connector']
                }
            ]
        }
    },
    'additionalProperties': False
}

_engine_schema = {
    'type': 'object',
    'properties': {
        'engine': {'type': 'string'},
        'settings': {'type': 'object'},
        'doc': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['engine', 'settings']
}


# Reproducible Experiment Description (RED)
red_schema = {
    'oneOf': [{
        'type': 'object',
        'properties': {
            'redVersion': {'type': 'string'},
            'cli': cwl_schema,
            'inputs': _inputs_schema,
            'outputs': _outputs_schema,
            'container': _engine_schema,
            'execution': _engine_schema,
            'doc': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['redVersion', 'cli', 'inputs', 'container']
    }, {
        'type': 'object',
        'properties': {
            'redVersion': {'type': 'string'},
            'cli': cwl_schema,
            'batches': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'inputs': _inputs_schema,
                        'outputs': _outputs_schema,
                        'doc': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['inputs']
                }
            },
            'container': _engine_schema,
            'execution': _engine_schema,
            'doc': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['redVersion', 'cli', 'batches', 'container']
    }]
}

#red_schema = transform(_red_schema)
