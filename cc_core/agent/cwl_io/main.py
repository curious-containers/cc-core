import json
import shutil
import tempfile
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read
from cc_core.commons.cwl_io import inputs_to_job
from cc_core.commons.cwl_io import cwl_io_validation, ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.cwl import cwl_to_command
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute
from cc_core.commons.exceptions import exception_format


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and RED connector files for remote inputs and ' \
              'outputs respectively.'


def attach_args(parser):
    parser.add_argument(
        '-c', '--cwl', action='store', type=str, metavar='CWL_FILE', required=True,
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '-i', '--inputs', action='store', type=str, metavar='INPUTS_FILE', required=True,
        help='INPUTS_FILE in the RED connectors format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '-o', '--outputs', action='store', type=str, metavar='OUTPUTS_FILE',
        help='OUTPUTS_FILE in the RED connectors format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '-d', '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    print(json.dumps(result, indent=4))

    return 0


def run(cwl, inputs, outputs, outdir):
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None
    }

    tmp_dir = tempfile.mkdtemp()

    try:
        cwl_data = load_and_read(cwl, 'CWL_FILE')
        inputs_data = load_and_read(inputs, 'INPUTS_FILE')
        outputs_data = load_and_read(outputs, 'OUTPUTS_FILE')

        cwl_io_validation(cwl_data, inputs_data, outputs_data)

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

        if outputs:
            send(connector_manager, output_files, outputs_data)
    except:
        result['debugInfo'] = exception_format()
    finally:
        shutil.rmtree(tmp_dir)

    return result
