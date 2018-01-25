from copy import deepcopy

from cc_core.commons.schemas.common import pattern_key


CWL_BASE_TYPES = ['string', 'int', 'long', 'float', 'double', 'boolean', 'File']
CWL_INPUT_ARRAY_TYPES = ['{}{}'.format(t, '[]') for t in CWL_BASE_TYPES[:-2]]
CWL_INPUT_TYPES = deepcopy(CWL_BASE_TYPES) + ['{}{}'.format(t, '?') for t in CWL_BASE_TYPES] + CWL_INPUT_ARRAY_TYPES
CWL_OUTPUT_TYPES = ['File', 'File?']


cwl_schema = {
    'type': 'object',
    'properties': {
        'cwlVersion': {'type': ['string', 'number']},
        'class': {'enum': ['CommandLineTool']},
        'baseCommand': {
            'oneOf': [
                {'type': 'string'},
                {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            ]
        },
        'doc': {'type': 'string'},
        'requirements': {
            'type': 'object',
            'properties': {
                'DockerRequirement': {
                    'type': 'object',
                    'properties': {
                        'dockerPull': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['dockerPull']
                }
            },
            'additionalProperties': False
        },
        'inputs': {
            'type': 'object',
            'patternProperties': {
                pattern_key: {
                    'type': 'object',
                    'properties': {
                        'type': {'enum': CWL_INPUT_TYPES},
                        'inputBinding': {
                            'type': 'object',
                            'properties': {
                                'prefix': {'type': 'string'},
                                'separate': {'type': 'boolean'},
                                'position': {'type': 'integer', 'minimum': 0},
                                'itemSeparator': {'type': 'string'}
                            },
                            'additionalProperties': False,
                        },
                        'doc': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['type', 'inputBinding']
                }
            }
        },
        'outputs': {
            'type': 'object',
            'patternProperties': {
                pattern_key: {
                    'type': 'object',
                    'properties': {
                        'type': {'enum': CWL_OUTPUT_TYPES},
                        'outputBinding': {
                            'type': 'object',
                            'properties': {
                                'glob': {'type': 'string'},
                            },
                            'additionalProperties': False,
                            'required': ['glob']
                        },
                        'doc': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['type', 'outputBinding']
                }
            }
        }
    },
    'additionalProperties': False,
    'required': ['cwlVersion', 'class', 'baseCommand', 'inputs', 'outputs']
}

cwl_job_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {
                    'type': 'object',
                    'properties': {
                        'class': {'enum': ['File']},
                        'path': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['class', 'path']
                },
                {
                    'type': 'object',
                    'properties': {
                        'class': {'enum': ['File']},
                        'location': {'type': 'string'}
                    },
                    'additionalProperties': False,
                    'required': ['class', 'location']
                },
                {
                    'type': 'array',
                    'items': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'number'}
                        ]
                    }
                }
            ]
        }
    }
}
