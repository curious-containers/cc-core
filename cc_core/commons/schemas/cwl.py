from cc_core.commons.schemas.common import pattern_key


URL_SCHEME_IDENTIFIER = 'path'


CWL_INPUT_TYPES = ['File', 'Directory', 'string', 'int', 'long', 'float', 'double', 'boolean']
CWL_INPUT_TYPES += ['{}[]'.format(t) for t in CWL_INPUT_TYPES[:-1]]
CWL_INPUT_TYPES += ['{}?'.format(t) for t in CWL_INPUT_TYPES[:]]

CWL_OUTPUT_TYPES = ['File', 'Directory']
CWL_OUTPUT_TYPES += ['{}?'.format(t) for t in CWL_OUTPUT_TYPES[:]]


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

_file_location_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'location': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['class', 'location']
}

_file_path_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        URL_SCHEME_IDENTIFIER: {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['class', URL_SCHEME_IDENTIFIER]
}

_directory_location_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'location': {'type': 'string'},
        'listing': {'type': 'array'}
    },
    'additionalProperties': False,
    'required': ['class', 'location']
}

_directory_path_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        URL_SCHEME_IDENTIFIER: {'type': 'string'},
        'listing': {'type': 'array'}
    },
    'additionalProperties': False,
    'required': ['class', URL_SCHEME_IDENTIFIER]
}

cwl_job_schema = {
    'type': 'object',
    'patternProperties': {
        pattern_key: {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                _file_location_schema,
                _file_path_schema,
                _directory_location_schema,
                _directory_path_schema,
                {
                    'type': 'array',
                    'items': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'number'},
                            _file_location_schema,
                            _file_path_schema,
                            _directory_location_schema,
                            _directory_path_schema
                        ]
                    }
                }
            ]
        }
    }
}

listing_sub_file_schema = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'basename': {'type': 'string'},
    },
    'required': ['class', 'basename'],
    'additionalProperties': False
}

listing_sub_directory_schema = {
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
cwl_job_listing_schema = {
    'type': 'array',
    'items': {
        'oneOf': [listing_sub_file_schema, listing_sub_directory_schema]
    }
}

