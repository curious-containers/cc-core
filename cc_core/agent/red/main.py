import json
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
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        'red_inputs_file', action='store', type=str, metavar='RED_INPUTS_FILE',
        help='RED_INPUTS_FILE in the RED connectors format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '-o', '--red-outputs-file', action='store', type=str, metavar='RED_OUTPUTS_FILE',
        help='RED_OUTPUTS_FILE in the RED connectors format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    dump_print(result, args.dump_format)

    return 0


def run(cwl_file, red_inputs_file, red_outputs_file, outdir, **_):
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None
    }

    tmp_dir = tempfile.mkdtemp()

    try:
        cwl_data = load_and_read(cwl_file, 'CWL_FILE')
        inputs_data = load_and_read(red_inputs_file, 'RED_INPUTS_FILE')
        outputs_data = load_and_read(red_outputs_file, 'RED_OUTPUTS_FILE')

        red_validation(cwl_data, inputs_data, outputs_data)

        connector_manager = ConnectorManager()
        import_and_validate_connectors(connector_manager, inputs_data, outputs_data)

        job_data = inputs_to_job(inputs_data, tmp_dir)
        command = cwl_to_command(cwl_data, job_data)
        result['command'] = command

        receive(connector_manager, inputs_data, tmp_dir)
        input_files = cwl_input_files(cwl_data, job_data)
        result['inputFiles'] = input_files

        cwl_input_file_check(input_files)
        process_data = execute(command)
        result['process'] = process_data

        output_files = cwl_output_files(cwl_data, output_dir=outdir)
        result['outputFiles'] = output_files

        cwl_output_file_check(output_files)

        if red_outputs_file:
            send(connector_manager, output_files, outputs_data)
    except:
        result['debugInfo'] = exception_format()
    finally:
        shutil.rmtree(tmp_dir)

    return result
