import sys
from collections import OrderedDict
from argparse import ArgumentParser

from cc_core.agent.connected.main import main as connected_main
from cc_core.agent.cwl_io.main import main as cwl_io_main
from cc_core.agent.cwl.main import main as cwl_main

from cc_core.agent.connected.main import DESCRIPTION as CONNECTED_DESCRIPTION
from cc_core.agent.cwl_io.main import DESCRIPTION as CWL_IO_DESCRIPTION
from cc_core.agent.cwl.main import DESCRIPTION as CWL_DESCRIPTION

SCRIPT_NAME = 'ccagent'

VERSION = '2.0.0'

DESCRIPTION = 'CC-Agent Copyright (C) 2017  Christoph Jansen. This software is distributed under the Apache 2.0 ' \
              'LICENSE and is part of the Curious Containers project (https://www.curious-containers.cc).'

MODES = OrderedDict([
    ('cwl', {'main': cwl_main, 'description': CWL_DESCRIPTION}),
    ('cwl-io', {'main': cwl_io_main, 'description': CWL_IO_DESCRIPTION}),
    ('connected', {'main': connected_main, 'description': CONNECTED_DESCRIPTION})
])


def main():
    sys.argv[0] = SCRIPT_NAME

    parser = ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        '-v', '--version', action='version', version=VERSION
    )
    subparsers = parser.add_subparsers(title='operation modes')

    sub_parser = None
    for key, val in MODES.items():
        sub_parser = subparsers.add_parser(key, help=val['description'], add_help=False)

    if len(sys.argv) < 2:
        parser.print_help()
        exit()

    _ = parser.parse_known_args()
    sub_args = sub_parser.parse_known_args()

    mode = MODES[sub_args[1][0]]['main']
    sys.argv[0] = '{} {}'.format(SCRIPT_NAME, sys.argv[1])
    del sys.argv[1]
    exit(mode())
