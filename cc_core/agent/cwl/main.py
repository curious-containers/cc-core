import os
import shutil
import tempfile
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump_print, move_files
from cc_core.commons.cwl import cwl_to_command, cwl_validation
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.cwl import cwl_input_directories, cwl_input_directories_check
from cc_core.commons.input_references import create_inputs_to_reference
from cc_core.commons.shell import execute, shell_result_check
from cc_core.commons.exceptions import exception_format, print_exception
from cc_core.commons.mnt_core import restore_original_environment

DESCRIPTION = 'Run a CommandLineTool as described in a CWLFILE and its corresponding JOBFILE.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWLFILE',
        help='CWLFILE containing a CLI description (json/yaml) as local PATH or http URL.'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOBFILE',
        help='JOBFILE in the CWL job format (json/yaml) as local PATH or http URL.'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Write debug info, including detailed exceptions, to stdout.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )
    parser.add_argument(
        '--leave-directories', action='store_true',
        help='Leave temporary inputs and working directories.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)

    format = args.__dict__['format']
    debug = args.__dict__['debug']
    if debug:
        dump_print(result, format)

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(cwl_file, job_file, leave_directories, **_):
    result = {
        'command': None,
        'inputFiles': None,
        'inputDirectories': None,
        'process': None,
        'outputFiles': None,
        'outputDirectories': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    tmp_working_dir = tempfile.mkdtemp()
    cwd = os.getcwd()

    try:
        restore_original_environment()

        cwl_data = load_and_read(cwl_file, 'CWLFILE')
        job_data = load_and_read(job_file, 'JOBFILE')

        cwl_validation(cwl_data, job_data)

        input_dir = os.path.split(os.path.expanduser(job_file))[0]

        command = cwl_to_command(cwl_data, job_data, input_dir=input_dir)
        result['command'] = command

        input_files = cwl_input_files(cwl_data, job_data, input_dir=input_dir)
        result['inputFiles'] = input_files
        cwl_input_file_check(input_files)

        input_directories = cwl_input_directories(cwl_data, job_data, input_dir=input_dir)
        result['inputDirectories'] = input_directories
        cwl_input_directories_check(input_directories)

        os.chdir(tmp_working_dir)
        process_data = execute(command)
        os.chdir(cwd)
        result['process'] = process_data
        shell_result_check(process_data)

        inputs_to_reference = create_inputs_to_reference(job_data, input_files, input_directories)

        output_files = cwl_output_files(cwl_data, inputs_to_reference, output_dir=tmp_working_dir)
        result['outputFiles'] = output_files
        cwl_output_file_check(output_files)

        move_files(output_files)
    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        print_exception(e)
    finally:
        if not leave_directories:
            shutil.rmtree(tmp_working_dir)

    return result
