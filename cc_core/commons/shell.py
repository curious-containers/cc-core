from subprocess import Popen, PIPE
from threading import Thread
from psutil import Process
from time import sleep
from threading import Lock
from time import time


SUPERVISION_INTERVAL_SECONDS = 1


def execute(command):
    sp = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)

    monitor = ProcessMonitor(sp)
    t = Thread(target=monitor.start)
    t.start()

    std_out, std_err = sp.communicate()
    return_code = sp.returncode
    monitoring_data = monitor.result()

    return {
        'stdOut': [l for l in std_out.decode('utf-8').split('\n') if l],
        'stdErr': [l for l in std_err.decode('utf-8').split('\n') if l],
        'returnCode': return_code,
        'monitoring': monitoring_data
    }


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
