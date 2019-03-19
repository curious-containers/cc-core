from cc_core.commons.schemas.common import _auth_schema
from cc_core.commons.schema_transform import transform


MIN_RAM_LIMIT = 256


_gpus_schema = {
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


_image_schema = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'auth': _auth_schema,
        'source': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'}
            },
            'additionalProperties': False,
            'required': ['url']
        }
    },
    'additionalProperties': False,
    'required': ['url']
}


_docker_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'image': _image_schema,
        'ram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
    },
    'additionalProperties': False,
    'required': ['image']
}


_nvidia_docker_schema = {
    'type': 'object',
    'properties': {
        'version': {'type': 'string'},
        'image': _image_schema,
        'gpus': _gpus_schema,
        'ram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
    },
    'additionalProperties': False,
    'required': ['image', 'gpus']
}


docker_schema = transform(_docker_schema)
nvidia_docker_schema = transform(_nvidia_docker_schema)


container_engines = {
    'docker': docker_schema,
    'nvidia-docker': nvidia_docker_schema
}
