from cc_core.commons.schemas.common import PATTERN_KEY
from cc_core.commons.schema_transform import transform


URL_SCHEME_IDENTIFIER = 'path'


CWL_INPUT_TYPES = ['File', 'Directory', 'string', 'int', 'long', 'float', 'double', 'boolean']
CWL_INPUT_TYPES += ['{}[]'.format(t) for t in CWL_INPUT_TYPES[:]]
CWL_INPUT_TYPES += ['{}?'.format(t) for t in CWL_INPUT_TYPES[:]]

CWL_OUTPUT_TYPES = ['File', 'Directory']
CWL_OUTPUT_TYPES += ['{}?'.format(t) for t in CWL_OUTPUT_TYPES[:]]


_cwl_schema = {
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
                PATTERN_KEY: {
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
                        }
                    },
                    'additionalProperties': False,
                    'required': ['type', 'inputBinding']
                }
            }
        },
        'outputs': {
            'type': 'object',
            'patternProperties': {
                PATTERN_KEY: {
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
                        }
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

_listing_sub_file_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'basename': {'type': 'string'},
    },
    'required': ['class', 'basename'],
    'additionalProperties': False
}

_listing_sub_directory_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'basename': {'type': 'string'},
        'listing': {'$ref': '#/'}
    },
    'additionalProperties': False,
    'required': ['class', 'basename']
}

# WARNING: Do not embed this schema into another schema,
# because this breaks the '$ref' in listing_sub_directory_schema
_cwl_job_listing_schema = {
    'type': 'array',
    'items': {
        'oneOf': [_listing_sub_file_schema, _listing_sub_directory_schema]
    }
}

cwl_job_listing_schema = transform(_cwl_job_listing_schema)
cwl_schema = transform(_cwl_schema)
