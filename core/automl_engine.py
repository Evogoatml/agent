# core/automl_engine.py
"""
AutoML Engine - Self-Optimization Core
-------------------------------------
This engine continuously monitors system performance,
tests parameter configurations, and adjusts runtime behavior
to improve stability and efficiency over time.
"""

import os
import json
import random
import time
from datetime import datetime
from statistics import mean

from core.diagnostics import Diagnostics
from core.memory_core import MemoryCore
from core.security import ZeroTrustGateway


class AutoMLEngine:
    def __init__(self, orchestrator=None):
        self.memory = MemoryCore()
        self.diagnostics = Diagnostics()
        self.security = ZeroTrustGateway()
        self.orchestrator = orchestrator

        self.config_path = "config/automl_state.json"
        self.load_state()

        self.governance_rules = {
            "max_cpu": 0.9,          # 90% CPU limit
            "max_mem": 0.85,         # 85% memory limit
            "safe_temp": 85,         # CPU safety temp
            "allowed_modules": [
                "memory_core",
                "scheduler",
                "diagnostics",
                "llm_interface",
                "orchestrator"
            ]
        }

        print("[AutoML] Engine initialized and monitoring...")

    # ----------------------------------------------------------
    # State Handling
    # ----------------------------------------------------------
    def load_state(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.state = json.load(f)
        else:
            self.state = {
                "last_update": str(datetime.now()),
                "metrics": {},
                "best_config": {},
                "performance_history": []
            }

    def save_state(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    # Core Optimization Loop
    # ----------------------------------------------------------
    def monitor_system(self):
        metrics = self.diagnostics.collect_metrics()
        self.state["metrics"] = metrics
        self.memory.store("latest_metrics", metrics)
        return metrics

    def evaluate_performance(self):
        metrics = self.state.get("metrics", {})
        score = 0

        # Simple baseline scoring
        if metrics:
            cpu = 1 - min(metrics.get("cpu_usage", 0.0), 1)
            mem = 1 - min(metrics.get("mem_usage", 0.0), 1)
            stability = metrics.get("stability_score", 0.5)
            score = mean([cpu, mem, stability])

        # Log performance
        self.state["performance_history"].append({
            "timestamp": str(datetime.now()),
            "score": score
        })

        return score

    def propose_adjustments(self, score):
        """Suggest new parameters if performance drops."""
        best = self.state.get("best_config", {})
        if not best or score > best.get("score", 0):
            self.state["best_config"] = {"score": score, "params": self.orchestrator.get_current_config()}
            print(f"[AutoML] New best configuration found (score: {score:.3f})")
            self.save_state()
            return None

        # If performance drops, test new configurations
        new_params = self.mutate_parameters(self.state["best_config"]["params"])
        print("[AutoML] Testing new parameter set:", new_params)
        self.orchestrator.apply_config(new_params)
        return new_params

    def mutate_parameters(self, params):
        """Randomized mutation for exploration."""
        mutated = params.copy()
        for key in mutated:
            if isinstance(mutated[key], (int, float)):
                jitter = random.uniform(0.95, 1.05)
                mutated[key] = round(mutated[key] * jitter, 5)
        return mutated

    # ----------------------------------------------------------
    # Governance and Constraints
    # ----------------------------------------------------------
    def verify_governance(self, metrics):
        """Ensure optimization stays within safety limits."""
        if metrics.get("cpu_usage", 0) > self.governance_rules["max_cpu"]:
            print("[AutoML][⚠] CPU usage exceeded safe limit. Rolling back.")
            self.rollback_best_config()
            return False
        if metrics.get("mem_usage", 0) > self.governance_rules["max_mem"]:
            print("[AutoML][⚠] Memory usage exceeded safe limit. Rolling back.")
            self.rollback_best_config()
            return False
        return True

    def rollback_best_config(self):
        """Revert to last known stable configuration."""
        best = self.state.get("best_config", {}).get("params")
        if best:
            print("[AutoML] Rolling back to last stable configuration.")
            self.orchestrator.apply_config(best)

    # ----------------------------------------------------------
    # Loop Execution
    # ----------------------------------------------------------
    def run(self):
        while True:
            metrics = self.monitor_system()
            score = self.evaluate_performance()
            safe = self.verify_governance(metrics)

            if safe:
                self.propose_adjustments(score)

            time.sleep(30)  # run every 30 seconds


if __name__ == "__main__":
    automl = AutoMLEngine()
    automl.run()
