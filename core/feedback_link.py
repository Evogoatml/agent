# core/feedback_link.py
"""
Feedback Synchronizer
---------------------
Facilitates continuous signal exchange between the Orchestrator
and AutoML engine. It passes telemetry, receives configuration
commands, and ensures safe rollbacks if conditions degrade.
"""

import time
import json
from datetime import datetime
from threading import Thread

from core.memory_core import MemoryCore
from core.security import ZeroTrustGateway


class FeedbackLink:
    def __init__(self, orchestrator, automl):
        self.orchestrator = orchestrator
        self.automl = automl
        self.memory = MemoryCore()
        self.security = ZeroTrustGateway()

        self.last_score = 0.0
        self.heartbeat_interval = 10
        self.feedback_log = "logs/feedback_history.json"
        print("[FeedbackLink] Established secure communication channel.")

    # ----------------------------------------------------------
    # Feedback Transmission
    # ----------------------------------------------------------
    def transmit_metrics(self):
        """Send live diagnostic metrics to AutoML."""
        metrics = self.orchestrator.run_diagnostics()
        encrypted = self.security.encrypt(json.dumps(metrics))
        self.memory.store("feedback_encrypted", encrypted)
        print(f"[FeedbackLink] Metrics transmitted (encrypted, {len(encrypted)} bytes).")

    def receive_adaptation(self):
        """Receive latest tuning suggestions from AutoML."""
        score = self.automl.evaluate_performance()
        if score < self.last_score * 0.95:  # drop threshold
            print("[FeedbackLink][⚠] Performance degradation detected, rollback triggered.")
            self.automl.rollback_best_config()
        else:
            new_params = self.automl.propose_adjustments(score)
            if new_params:
                self.orchestrator.apply_config(new_params)
        self.last_score = score

    # ----------------------------------------------------------
    # Heartbeat Loop
    # ----------------------------------------------------------
    def run(self):
        print("[FeedbackLink] Synchronization loop active.")
        while True:
            try:
                self.transmit_metrics()
                self.receive_adaptation()
                self.log_feedback()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"[FeedbackLink][ERROR] {e}")
                time.sleep(5)

    def log_feedback(self):
        """Persist a history for learning review."""
        log = {
            "timestamp": str(datetime.now()),
            "score": self.last_score,
            "config": self.orchestrator.get_current_config(),
        }
        try:
            with open(self.feedback_log, "a") as f:
                f.write(json.dumps(log) + "\n")
        except Exception:
            pass


# Standalone test harness
if __name__ == "__main__":
    from orchestrator import Orchestrator
    from core.automl_engine import AutoMLEngine

    orch = Orchestrator()
    aml = AutoMLEngine(orchestrator=orch)
    link = FeedbackLink(orch, aml)

    # Run in separate thread
    Thread(target=link.run, daemon=True).start()

    # Keep main alive
    while True:
        time.sleep(60)
