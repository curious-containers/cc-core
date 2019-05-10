import os
from subprocess import Popen, PIPE
from threading import Thread

from cc_core.commons.exceptions import JobExecutionError


SUPERVISION_INTERVAL_SECONDS = 1


def prepare_outdir(outdir):
    """
    Creates the output directory if not existing.
    If outdir is None or if no output_files are provided nothing happens.

    :param outdir: The output directory to create.
    """
    if outdir:
        outdir = os.path.expanduser(outdir)
        if not os.path.isdir(outdir):
            try:
                os.makedirs(outdir)
            except os.error as e:
                raise JobExecutionError('Failed to create outdir "{}".\n{}'.format(outdir, str(e)))


def execute(command):
    try:
        sp = Popen(command, stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True, encoding='utf-8')
    except TypeError:
        sp = Popen(command, stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True)

    monitor = ProcessMonitor(sp)
    t = Thread(target=monitor.start)
    t.start()

    std_out, std_err = sp.communicate()
    return_code = sp.returncode
    monitoring_data = monitor.result()

    return {
        'stdOut': [l for l in std_out.split(os.linesep) if l],
        'stdErr': [l for l in std_err.split(os.linesep) if l],
        'returnCode': return_code,
        'monitoring': monitoring_data
    }


def shell_result_check(process_data):
    if process_data['returnCode'] != 0:
        raise JobExecutionError('process returned non-zero exit code "{}"\nProcess stderr:\n{}'
                                .format(process_data['returnCode'], process_data['stdErr']))

