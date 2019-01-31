import os
from subprocess import Popen, PIPE
from threading import Thread
from psutil import Process
from time import sleep
from threading import Lock
from time import time

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
    sp = Popen(command, stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True, encoding='utf-8')

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


class ProcessMonitor:
    def __init__(self, process):
        self.process = process
        self.max_vms_memory = 0
        self.max_rss_memory = 0
        self.lock = Lock()
        self.timestamp = time()

    def start(self):
        # source: http://stackoverflow.com/a/13607392
        while True:
            try:
                pp = Process(self.process.pid)
                processes = list(pp.children(recursive=True))
                processes.append(pp)

                vms_memory = 0
                rss_memory = 0

                for p in processes:
                    try:
                        mem_info = p.memory_info()
                        rss_memory += mem_info[0]
                        vms_memory += mem_info[1]
                    except:
                        pass
                with self.lock:
                    self.max_vms_memory = max(self.max_vms_memory, vms_memory)
                    self.max_rss_memory = max(self.max_rss_memory, rss_memory)
            except:
                break
            sleep(SUPERVISION_INTERVAL_SECONDS)

    def result(self):
        with self.lock:
            return {
                'maxVMSMemory': self.max_vms_memory / (1024 * 1024),
                'maxRSSMemory': self.max_rss_memory / (1024 * 1024),
                'wallTime': time() - self.timestamp
            }
