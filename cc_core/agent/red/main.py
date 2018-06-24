import shutil
import tempfile
from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read, dump_print
from cc_core.commons.red import inputs_to_job, convert_batch_experiment
from cc_core.commons.red import red_validation, ConnectorManager, import_and_validate_connectors, receive, send
from cc_core.commons.cwl import cwl_to_command
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute, shell_result_check
from cc_core.commons.exceptions import exception_format, RedValidationError
from cc_core.commons.jinja import jinja_validation, template_values, fill_template


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and RED connector files for remote inputs and ' \
              'outputs respectively.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '-j', '--jinja-file', action='store', type=str, metavar='JINJA_FILE',
        help='JINJA_FILE (json or yaml) containing values for jinja template variables in RED_FILE as local path '
             'or http url.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )
    parser.add_argument(
        '--batch', action='store', type=int, metavar='BATCH',
        help='If the RED_FILE contains batches, the index of a BATCH, starting with 0, must be passed.'
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

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(red_file, jinja_file, batch, outdir, ignore_outputs, **_):
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    tmp_dir = tempfile.mkdtemp()
    template_vals = None

    try:
        red_raw = load(red_file, 'RED_FILE')

        jinja_data = None
        if jinja_file:
            jinja_data = load_and_read(jinja_file, 'JINJA_FILE')
            jinja_validation(jinja_data)

        template_vals = template_values(red_raw, jinja_data)
        red_raw_filled = fill_template(red_raw, template_vals)
        red_data = read(red_raw_filled, 'RED_FILE')
        red_validation(red_data, ignore_outputs)

        red_data = convert_batch_experiment(red_data, batch)

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
        shell_result_check(process_data)

        output_files = cwl_output_files(red_data['cli'], output_dir=outdir)
        result['outputFiles'] = output_files
        cwl_output_file_check(output_files)

        if not ignore_outputs and red_data.get('outputs'):
            send(connector_manager, output_files, red_data)
    except RedValidationError:
        result['debugInfo'] = exception_format(template_vals=template_vals)
        result['state'] = 'failed'
    except:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
    finally:
        shutil.rmtree(tmp_dir)

    return result
