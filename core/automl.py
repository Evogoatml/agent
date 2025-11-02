import random, time

class AutoML:
    def __init__(self):
        self.metrics = {}

    def start_monitoring(self):
        print("[AutoML] Runtime optimization active.")

    def optimize(self, data):
        latency = random.uniform(0.1, 0.3)
        time.sleep(latency)
        self.metrics["last_latency"] = latency
        return f"[Optimized] {data}"
