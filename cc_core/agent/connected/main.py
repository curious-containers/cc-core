import os
import tempfile
import requests
from argparse import ArgumentParser

from cc_core.commons.red import inputs_to_job, red_validation
from cc_core.commons.red import ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.templates import inspect_templates_and_secrets, fill_template
from cc_core.commons.cwl import cwl_to_command
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute, shell_result_check
from cc_core.commons.exceptions import exception_format


DESCRIPTION = 'In order to run an application container with Curious Containers, CC-Agency will launch ccagent in ' \
              'connected mode. The agent sends the container\'s internal status to the server and receives ' \
              'instructions.'


def attach_args(parser):
    parser.add_argument(
        'callback_url', action='store', type=str, metavar='CALLBACK_URL',
        help='An individual CALLBACK_URL is generated by CC-Server for the corresponding agent.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )
    parser.add_argument(
        '--inspect', action='store_true',
        help='The agent will only perform one callback to inspect if CC-Agency is reachable via the network.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(callback_url, outdir, inspect):
    if inspect:
        r = requests.get(callback_url)
        r.raise_for_status()
        return

    r = requests.get(callback_url)
    r.raise_for_status()
    red_data = r.json()
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tempfile.mkdtemp())

    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    secret_values = None

    try:
        red_validation(red_data, False)
        _, secret_values = inspect_templates_and_secrets(red_data, None, True)
        red_data = fill_template(red_data, None, False, True)

        connector_manager = ConnectorManager()
        import_and_validate_connectors(connector_manager, red_data, False)

        job_data = inputs_to_job(red_data, tmp_dir)
        command = cwl_to_command(red_data['cli'], job_data)
        result['command'] = command

        receive(connector_manager, red_data, tmp_dir)
        input_files = cwl_input_files(red_data['cli'], job_data)
        result['inputFiles'] = input_files
        cwl_input_file_check(input_files)

        process_data = execute(command)
        result['process'] = process_data
        shell_result_check(process_data)

        output_files = cwl_output_files(red_data['cli'], output_dir=outdir)
        result['outputFiles'] = output_files
        cwl_output_file_check(output_files)

        send(connector_manager, output_files, red_data)
    except Exception:
        result['debugInfo'] = exception_format(secret_values=secret_values)
        result['state'] = 'failed'

    r = requests.post(callback_url, json=result)
    r.raise_for_status()
