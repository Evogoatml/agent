import time
import threading
from typing import Callable, Dict, Any, Optional

class Job:
    def __init__(self, name: str, every_sec: float, fn: Callable, *args, **kwargs):
        self.name = name
        self.every_sec = every_sec
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.next_at = time.time() + every_sec

class Scheduler:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def add(self, name: str, every_sec: float, fn: Callable, *args, **kwargs):
        self.jobs[name] = Job(name, every_sec, fn, *args, **kwargs)

    def remove(self, name: str):
        self.jobs.pop(name, None)

    def start(self):
        self._t.start()

    def _loop(self):
        while not self._stop.is_set():
            now = time.time()
            for j in list(self.jobs.values()):
                if now >= j.next_at:
                    try:
                        j.fn(*j.args, **j.kwargs)
                    finally:
                        j.next_at = time.time() + j.every_sec
            time.sleep(0.2)

    def stop(self):
        self._stop.set()
        self._t.join(timeout=0.5)
