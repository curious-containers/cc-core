_dependencies_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'personal_package_archives': {
            'type': 'list',
            'items': {'type': 'string'}
        },
        'apt_packages': {
            'type': 'list',
            'items': {'type': 'string'}
        }
    },
    'additionalProperties': False
}

ubuntu_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'version': {'type': 'string'},
        'dependencies': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'build': _dependencies_schema,
                'execution': _dependencies_schema
            },
            'additionalProperties': False
        }
    },
    'additionalProperties': False
}

os_engines = {
    'ubuntu': ubuntu_schema
}
