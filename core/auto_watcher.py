import os
import time
import threading
from typing import List, Callable

class AutoWatcher:
    def __init__(self, paths: List[str], on_change: Callable[[], None], interval: float = 1.5):
        self.paths = paths
        self.on_change = on_change
        self.interval = interval
        self._mtimes = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _snapshot(self):
        snap = {}
        for base in self.paths:
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for f in files:
                    if f.endswith(".py"):
                        p = os.path.join(root, f)
                        try:
                            snap[p] = os.path.getmtime(p)
                        except FileNotFoundError:
                            pass
        return snap

    def _loop(self):
        self._mtimes = self._snapshot()
        while not self._stop.is_set():
            time.sleep(self.interval)
            snap = self._snapshot()
            if snap != self._mtimes:
                self._mtimes = snap
                try:
                    self.on_change()
                except Exception:
                    pass

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=0.5)
