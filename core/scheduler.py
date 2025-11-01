import threading, time

class Scheduler:
    def __init__(self):
        self.jobs = []

    def every(self, interval, func, *args, **kwargs):
        def job():
            while True:
                func(*args, **kwargs)
                time.sleep(interval)
        t = threading.Thread(target=job, daemon=True)
        t.start()
        self.jobs.append(t)
