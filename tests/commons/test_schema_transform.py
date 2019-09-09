import jsonschema

from cc_core.commons.schema_transform import transform


PATTERN_KEY = '^[a-zA-Z0-9_-]+$'


def test_transform_1():
    source_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['key1', 'key2']
    }

    target_schema = {
        'type': 'object',
        'properties': {
            'doc': {'oneOf': [
                {'type': 'string'},
                {'type': 'null'}
            ]},
            'key1': {'type': 'string'},
            'key2': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['key1', 'key2']
    }

    transformed_schema = transform(source_schema)

    assert target_schema == transformed_schema

    data = {
        'doc': 'content',
        'key1': 'content',
        'key2': {}
    }

    jsonschema.validate(data, transformed_schema)


def test_transform_2():
    source_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['key2']
    }

    target_schema = {
        'type': 'object',
        'properties': {
            'doc': {'oneOf': [
                {'type': 'string'},
                {'type': 'null'}
            ]},
            'key1': {
                'oneOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ]
            },
            'key2': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['key2']
    }

    transformed_schema = transform(source_schema)

    assert target_schema == transformed_schema

    data = {
        'doc': 'content',
        'key1': 'content',
        'key2': {}
    }

    jsonschema.validate(data, transformed_schema)

    data = {
        'doc': None,
        'key2': {}
    }

    jsonschema.validate(data, transformed_schema)

    data = {
        'doc': 'content',
        'key1': None,
        'key2': {}
    }

    jsonschema.validate(data, transformed_schema)


def test_transform_3():
    source_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['key1']
    }

    target_schema = {
        'type': 'object',
        'properties': {
            'doc': {'oneOf': [
                {'type': 'string'},
                {'type': 'null'}
            ]},
            'key1': {'type': 'string'},
            'key2': {
                'oneOf': [
                    {'type': 'object'},
                    {'type': 'null'}
                ]
            }
        },
        'additionalProperties': False,
        'required': ['key1']
    }

    transformed_schema = transform(source_schema)

    assert target_schema == transformed_schema

    data = {
        'doc': 'content',
        'key1': 'content',
        'key2': {}
    }

    jsonschema.validate(data, transformed_schema)

    data = {
        'doc': 'content',
        'key1': 'content'
    }

    jsonschema.validate(data, transformed_schema)

    data = {
        'key1': 'content',
        'key2': None
    }

    jsonschema.validate(data, transformed_schema)


def test_transform_4():
    source_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {
                'type': 'array',
                'items': {
                    'anyOf': [
                        {'type': 'string'},
                        {
                            'type': 'object',
                            'properties': {
                                'foo': {'enum': ['hello', 'world']},
                                'bar': {'type': 'integer'}
                            },
                            'additionalProperties': False,
                            'required': ['bar']
                        }
                    ]
                }
            },
            'key3': {
                'type': 'object',
                'patterProperties': {
                    PATTERN_KEY: {
                        'type': 'object',
                        'properties': {
                            'foo': {'type': 'string'},
                            'bar': {'type': 'string'}
                        },
                        'additionalProperties': False
                    }
                }
            }
        },
        'additionalProperties': False,
        'required': ['key1']
    }

    transformed_schema = transform(source_schema)

    data = {
        'doc': None,
        'key1': 'content',
        'key3': {
            'baz': {
                'foo': None
            }
        }
    }

    jsonschema.validate(data, transformed_schema)

    data = {
        'key1': 'content',
        'key2': [
            'hello world',
            {
                'foo': 'hello',
                'bar': 42
            },
            {
                'doc': 'content',
                'bar': 42
            },
            {
                'foo': None,
                'bar': 42
            }
        ],
        'key3': {
            'baz': {
                'foo': None
            }
        }
    }

    jsonschema.validate(data, transformed_schema)


def test_null_values():
    source_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {
                'oneOf': [
                    {'type': 'object'},
                    {'type': 'null'}
                ]
            }
        },
        'additionalProperties': False,
        'required': ['key1']
    }

    transformed_schema = transform(source_schema)

    target_schema = {
        'type': 'object',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {
                'oneOf': [
                    {'type': 'object'},
                    {'type': 'null'}
                ]
            },
            'doc': {
                'oneOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ]
            }
        },
        'additionalProperties': False,
        'required': ['key1']
    }

    assert transformed_schema == target_schema
