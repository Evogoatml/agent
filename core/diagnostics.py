import psutil

class Diagnostics:
    def self_check(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        print(f"[Diagnostics] CPU: {cpu}% | MEM: {mem}%")
        if mem > 90:
            print("[Diagnostics] Warning: High memory usage")
