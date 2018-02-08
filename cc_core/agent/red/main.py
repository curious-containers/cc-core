import shutil
import tempfile
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump_print
from cc_core.commons.red import inputs_to_job
from cc_core.commons.red import red_validation, ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.cwl import cwl_to_command
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute
from cc_core.commons.exceptions import exception_format


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and RED connector files for remote inputs and ' \
              'outputs respectively.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
    )
    parser.add_argument(
        '--ignore-outputs', action='store_true',
        help='Ignore RED connectors specified in RED_FILE outputs section.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    dump_print(result, args.dump_format)

    return 0


def run(red_file, outdir, ignore_outputs, **_):
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None
    }

    tmp_dir = tempfile.mkdtemp()

    try:
        red_data = load_and_read(red_file, 'RED_FILE')
        red_validation(red_data, ignore_outputs)

        connector_manager = ConnectorManager()
        import_and_validate_connectors(connector_manager, red_data, ignore_outputs)

        job_data = inputs_to_job(red_data, tmp_dir)
        command = cwl_to_command(red_data['cli'], job_data)
        result['command'] = command

        receive(connector_manager, red_data, tmp_dir)
        input_files = cwl_input_files(red_data['cli'], job_data)
        result['inputFiles'] = input_files

        cwl_input_file_check(input_files)
        process_data = execute(command)
        result['process'] = process_data

        output_files = cwl_output_files(red_data['cli'], output_dir=outdir)
        result['outputFiles'] = output_files

        cwl_output_file_check(output_files)

        if not ignore_outputs and red_data.get('outputs'):
            send(connector_manager, output_files, red_data)
    except:
        result['debugInfo'] = exception_format()
    finally:
        shutil.rmtree(tmp_dir)

    return result
