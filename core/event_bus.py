import threading
from collections import defaultdict
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._sub: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: Callable[[Any], None]):
        with self._lock:
            self._sub[topic].append(handler)

    def publish(self, topic: str, data: Any = None):
        handlers = []
        with self._lock:
            handlers = list(self._sub.get(topic, []))
        for h in handlers:
            try:
                h(data)
            except Exception:
                pass  # handlers must be robust
