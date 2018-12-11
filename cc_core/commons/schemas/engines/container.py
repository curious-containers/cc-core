from cc_core.commons.schemas.common import auth_schema


MIN_RAM_LIMIT = 256


gpus_schema = {
    'oneOf': [{
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'minVram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
            },
            'additionalProperties': False
        }
    }, {
        'type': 'object',
        'properties': {
            'count': {'type': 'integer'}
        },
        'additionalProperties': False,
        'required': ['count']
    }]
}


image_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'url': {'type': 'string'},
        'auth': auth_schema,
        'source': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'url': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['url']
        }
    },
    'additionalProperties': False,
    'required': ['url']
}


docker_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'image': image_schema,
        'ram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
    },
    'additionalProperties': False,
    'required': ['image']
}


nvidia_docker_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'image': image_schema,
        'gpus': gpus_schema,
        'ram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
    },
    'additionalProperties': False,
    'required': ['image', 'gpus']
}


container_engines = {
    'docker': docker_schema,
    'nvidia-docker': nvidia_docker_schema
}
