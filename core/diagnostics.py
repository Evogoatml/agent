import os, json, time

class Diagnostics:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, "agent.log")

    def record(self, event, data=None):
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": event,
            "data": data or {}
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def tail(self, n=20):
        with open(self.path, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-n:])
