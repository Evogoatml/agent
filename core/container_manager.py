import subprocess
import multiprocessing
import os

class ContainerManager:
    def __init__(self):
        self.processes = {}

    def spawn(self, name, command):
        print(f"[ContainerManager] Launching {name}")
        proc = multiprocessing.Process(target=self._run_process, args=(command,))
        proc.start()
        self.processes[name] = proc

    def _run_process(self, command):
        os.system(command)

    def list_active(self):
        return [name for name, proc in self.processes.items() if proc.is_alive()]

    def stop_all(self):
        for name, proc in self.processes.items():
            print(f"[ContainerManager] Terminating {name}")
            proc.terminate()
