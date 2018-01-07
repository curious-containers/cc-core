import os
from pprint import pprint
from argparse import ArgumentParser

from cc_core.commons.files import read_file, loads
from cc_core.commons.cwl import cwl_to_command, cwl_validation
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE. Refer to the CWL ' \
              'documentation (http://www.commonwl.org) for more details.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOB_FILE',
        help='JOB_FILE in the CWL job format (json/yaml) as local path or http url'
    )
    parser.add_argument(
        '-o', '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(cwl_file, job_file, outdir):
    cwl_raw = read_file(cwl_file)
    job_raw = read_file(job_file)

    cwl_data = loads(cwl_raw)
    job_data = loads(job_raw)

    cwl_validation(cwl_data, job_data)

    input_dir = os.path.split(os.path.expanduser(job_file))[0]

    command = cwl_to_command(cwl_data, job_data, input_dir)
    print('COMMAND:')
    print(command)

    input_files = cwl_input_files(cwl_data, job_data, input_dir=input_dir)
    print()
    print('INPUT FILES:')
    pprint(input_files)

    cwl_input_file_check(input_files)

    process_data = execute(command)
    print()
    print('PROCESS:')
    pprint(process_data)

    output_files = cwl_output_files(cwl_data, output_dir=outdir)
    print()
    print('OUTPUT FILES:')
    pprint(output_files)
    cwl_output_file_check(output_files)

    return 0
