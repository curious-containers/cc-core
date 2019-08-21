from cc_core.commons.schemas.common import _auth_schema
from cc_core.commons.schema_transform import transform


MIN_RAM_LIMIT = 256
SUPPORTED_GPU_VENDORS = ['nvidia']


_gpus_schema = {
    'oneOf': [
        {
            'type': 'object',
            'properties': {
                'vendor': {'enum': SUPPORTED_GPU_VENDORS},
                'count': {'type': 'integer'},
            },
            'additionalProperties': False,
            'required': ['vendor', 'count']
        },
        {
            'type': 'object',
            'properties': {
                'vendor': {'enum': SUPPORTED_GPU_VENDORS},
                'devices': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'minVram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
                        },
                        'additionalProperties': False
                    }
                }
            },
            'additionalProperties': False,
            'required': ['vendor', 'devices']
        }
    ]
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
        'gpus': _gpus_schema,
        'ram': {'type': 'integer', 'minimum': MIN_RAM_LIMIT}
    },
    'additionalProperties': False,
    'required': ['image']
}


docker_schema = transform(_docker_schema)


container_engines = {
    'docker': docker_schema,
}
