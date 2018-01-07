import shutil
import tempfile
from pprint import pprint
from argparse import ArgumentParser

from cc_core.commons.files import read_file, loads
from cc_core.commons.cwl_io import inputs_to_job
from cc_core.commons.cwl_io import cwl_io_validation, ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.cwl import cwl_to_command
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and FAICE connector files for remote inputs and ' \
              'outputs respectively. Refer to CWL (http://www.commonwl.org) and FAICE ' \
              'documentations for more details.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url'
    )
    parser.add_argument(
        'inputs_file', action='store', type=str, metavar='INPUTS_FILE',
        help='INPUTS_FILE in the FAICE connectors format (json/yaml) as local path or http url'
    )
    parser.add_argument(
        'outputs_file', action='store', type=str, metavar='OUTPUTS_FILE',
        help='OUTPUTS_FILE in the FAICE connectors format (json/yaml) as local path or http url'
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


def run(cwl_file, inputs_file, outputs_file, outdir):
    cwl_raw = read_file(cwl_file)
    inputs_raw = read_file(inputs_file)
    outputs_raw = read_file(outputs_file)

    cwl_data = loads(cwl_raw)
    inputs_data = loads(inputs_raw)
    outputs_data = loads(outputs_raw)

    cwl_io_validation(cwl_data, inputs_data, outputs_data)

    connector_manager = ConnectorManager()
    import_and_validate_connectors(connector_manager, inputs_data, outputs_data)

    tmp_dir = tempfile.mkdtemp()

    try:
        job_data = inputs_to_job(inputs_data, tmp_dir)
        command = cwl_to_command(cwl_data, job_data)
        print('COMMAND:')
        print(command)

        receive(connector_manager, inputs_data, tmp_dir)
        input_files = cwl_input_files(cwl_data, job_data)
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
        send(connector_manager, output_files, outputs_data)
    finally:
        shutil.rmtree(tmp_dir)

    return 0
