#!/usr/bin/env python3

from distutils.core import setup

description = 'CC-Core is part of the Curious Containers project. It provides common functionality for other parts of' \
              'Curious Containers and implements an agent for CLI tool execution.'

setup(
    name='cc-core',
    version='2.0.0',
    summary=description,
    description=description,
    author='Christoph Jansen',
    author_email='Christoph.Jansen@htw-berlin.de',
    url='https://github.com/curious-containers/cc-core',
    packages=[
        'cc_core',
        'cc_core.commons',
        'cc_core.commons.schemas',
        'cc_core.commons.schemas.engines',
        'cc_core.agent',
        'cc_core.agent.cwl',
        'cc_core.agent.cwl_io',
        'cc_core.agent.connected'
    ],
    entry_points={
        'console_scripts': ['ccagent=cc_core.agent.main:main']
    },
    license='AGPL-3.0',
    platforms=['any'],
    install_requires=[
        'flask',
        'requests',
        'jsonschema',
        'ruamel.yaml',
        'psutil'
    ]
)
