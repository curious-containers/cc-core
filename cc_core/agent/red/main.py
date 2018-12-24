import os
import shutil
import tempfile
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump_print, move_files
from cc_core.commons.input_references import create_inputs_to_reference
from cc_core.commons.red import inputs_to_job, convert_batch_experiment
from cc_core.commons.red import red_validation, ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.cwl import cwl_to_command, cwl_input_directories, cwl_input_directories_check
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute, shell_result_check
from cc_core.commons.exceptions import exception_format, RedValidationError, print_exception
from cc_core.commons.templates import fill_validation, inspect_templates_and_secrets, fill_template


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and RED connector files for remote inputs and ' \
              'outputs respectively.'


def attach_args(parser):
    parser.add_argument(
        'red', action='store', type=str, metavar='FILE_PATH_OR_URL',
        help='RED FILE (json or yaml) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '-v', '--variables', action='store', type=str, metavar='FILE_PATH_OR_URL',
        help='FILE (json or yaml) containing key-value pairs for variables in RED FILE as '
             'local PATH or http URL.'
    )
    parser.add_argument(
        '-b', '--batch', action='store', type=int, metavar='INDEX',
        help='If the RED FILE contains batches, the INDEX of a batch, starting with 0, must be passed.'
    )
    parser.add_argument(
        '-o', '--outputs', action='store_true',
        help='Enable connectors specified in the RED FILE outputs section.'
    )
    parser.add_argument(
        '-m', '--meta', action='store_true',
        help='Write meta data, including detailed exceptions, to stdout.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify meta data FORMAT as one of [json, yaml, yml]. Default is yaml.'
    )
    parser.add_argument(
        '--disable-rm', action='store_true',
        help='Disable removal of temporary inputs and working directories.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)

    meta = args.__dict__['meta']

    if meta:
        format = args.__dict__['format']
        dump_print(result, format)

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(red, variables, batch, outputs, disable_rm, **_):
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    tmp_inputs_dir = tempfile.mkdtemp()
    tmp_working_dir = tempfile.mkdtemp()
    cwd = os.getcwd()

    secret_values = None

    try:
        red_data = load_and_read(red, 'RED FILE')
        ignore_outputs = not outputs
        red_validation(red_data, ignore_outputs)

        variables_data = None
        if variables:
            variables_data = load_and_read(variables, 'VARIABLES FILE')
            fill_validation(variables_data)

        red_data = convert_batch_experiment(red_data, batch)

        template_keys_and_values, secret_values = inspect_templates_and_secrets(red_data, variables_data, True)
        red_data = fill_template(red_data, template_keys_and_values, False, True)

        connector_manager = ConnectorManager()
        import_and_validate_connectors(connector_manager, red_data, ignore_outputs)

        job_data = inputs_to_job(red_data, tmp_inputs_dir)
        command = cwl_to_command(red_data['cli'], job_data)
        result['command'] = command

        receive(connector_manager, red_data, tmp_inputs_dir)
        input_files = cwl_input_files(red_data['cli'], job_data)
        result['inputFiles'] = input_files
        cwl_input_file_check(input_files)

        input_directories = cwl_input_directories(red_data['cli'], job_data)
        result['inputDirectories'] = input_directories
        cwl_input_directories_check(input_directories)

        # prepare_outdir(outdir)
        os.chdir(tmp_working_dir)
        process_data = execute(command, None)
        os.chdir(cwd)
        result['process'] = process_data
        shell_result_check(process_data)

        inputs_to_reference = create_inputs_to_reference(job_data, input_files, input_directories)

        output_files = cwl_output_files(red_data['cli'], inputs_to_reference, output_dir=tmp_working_dir)
        result['outputFiles'] = output_files
        cwl_output_file_check(output_files)

        if outputs:
            if red_data.get('outputs'):
                send(connector_manager, output_files, red_data)
        else:
            move_files(output_files)


    except RedValidationError as e:
        result['debugInfo'] = exception_format(secret_values=secret_values)
        result['state'] = 'failed'
        print_exception(e)
    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        print_exception(e)
    finally:
        if not disable_rm:
            shutil.rmtree(tmp_inputs_dir)
            shutil.rmtree(tmp_working_dir)

    return result
