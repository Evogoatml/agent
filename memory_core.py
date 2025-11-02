import os
import sqlite3
import json
import time
import statistics
from datetime import datetime
from threading import Thread, Event
from core.orchestrator_secure import OrchestratorSecure

DB_PATH = "memory/store.db"
os.makedirs("memory", exist_ok=True)

class MemoryCore:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.stop_flag = Event()
        self.feedback_thread = Thread(target=self._feedback_loop, daemon=True)
        self.feedback_thread.start()

    def _create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT,
            function TEXT,
            args TEXT,
            kwargs TEXT,
            result TEXT,
            duration REAL,
            status TEXT,
            timestamp TEXT
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT,
            created_at TEXT
        )""")
        self.conn.commit()

    def log_execution(self, module, function, args, kwargs, result, duration, status):
        self.cursor.execute("""
        INSERT INTO executions (module, function, args, kwargs, result, duration, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (module, function, json.dumps(args), json.dumps(kwargs),
         str(result), duration, status, datetime.utcnow().isoformat()))
        self.conn.commit()

    def _feedback_loop(self):
        while not self.stop_flag.is_set():
            time.sleep(10)
            self.generate_feedback()

    def generate_feedback(self):
        self.cursor.execute("SELECT module, function, duration, status FROM executions WHERE timestamp >= datetime('now','-5 minutes')")
        rows = self.cursor.fetchall()
        if not rows:
            return
        total = len(rows)
        avg_time = statistics.mean([r[2] for r in rows]) if rows else 0
        errors = [r for r in rows if r[3] != 'OK']
        msg = {
            "window": "5m",
            "total_calls": total,
            "avg_exec_time": round(avg_time, 4),
            "error_rate": round(len(errors) / total, 3)
        }
        self.cursor.execute("INSERT INTO feedback (summary, created_at) VALUES (?, ?)", (json.dumps(msg), datetime.utcnow().isoformat()))
        self.conn.commit()

    def get_feedback(self, limit=10):
        self.cursor.execute("SELECT summary, created_at FROM feedback ORDER BY id DESC LIMIT ?", (limit,))
        return [{"summary": json.loads(r[0]), "time": r[1]} for r in self.cursor.fetchall()]

    def close(self):
        self.stop_flag.set()
        self.feedback_thread.join(timeout=1)
        self.conn.close()

memory_core = MemoryCore()
