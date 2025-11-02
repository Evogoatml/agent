import time
import queue
import threading
from typing import Callable, Any, Optional, Dict

class TaskQueue:
    def __init__(self, workers: int = 2):
        self.q = queue.PriorityQueue()
        self.shutdown_flag = threading.Event()
        self.threads = []
        for _ in range(workers):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.threads.append(t)

    def _worker(self):
        while not self.shutdown_flag.is_set():
            try:
                prio, ts, fn, args, kwargs = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                fn(*args, **kwargs)
            finally:
                self.q.task_done()

    def put(self, fn: Callable, *args, priority: int = 10, **kwargs):
        self.q.put((priority, time.time(), fn, args, kwargs))

    def stop(self):
        self.shutdown_flag.set()
        for t in self.threads:
            t.join(timeout=0.5)
