#!/bin/bash
set -e

echo "=== Bootstrapping Super AI Core ==="

# --- Create directories ---
mkdir -p core logs data memory plugins

# --- __init__.py ---
cat > core/__init__.py <<'EOF'
# Core package init
EOF

# --- Diagnostics ---
cat > core/diagnostics.py <<'EOF'
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
EOF

# --- Memory ---
cat > core/memory.py <<'EOF'
import json, os

class Memory:
    def __init__(self, path="memory/memory.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, "w") as f: json.dump({}, f)

    def load(self):
        with open(self.path, "r") as f: return json.load(f)

    def save(self, data):
        with open(self.path, "w") as f: json.dump(data, f, indent=2)

    def add(self, key, value):
        mem = self.load(); mem[key] = value; self.save(mem)
EOF

# --- Scheduler ---
cat > core/scheduler.py <<'EOF'
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
EOF

# --- Security ---
cat > core/security.py <<'EOF'
import hashlib

class Security:
    @staticmethod
    def hash_text(text):
        return hashlib.sha256(text.encode()).hexdigest()
EOF

# --- Enclave Gateway (controller interface) ---
cat > core/enclave_gateway.py <<'EOF'
from core.llm_interface import LLMInterface
from core.diagnostics import Diagnostics
from core.memory import Memory

class EnclaveGateway:
    def __init__(self):
        self.llm = LLMInterface()
        self.log = Diagnostics()
        self.memory = Memory()

    def process_request(self, prompt):
        self.log.record("request_received", {"prompt": prompt})
        response = self.llm.query(prompt)
        self.memory.add("last_response", response)
        self.log.record("response_generated", {"response": response[:200]})
        return response
EOF

# --- LLM Interface ---
cat > core/llm_interface.py <<'EOF'
import os
from openai import OpenAI

class LLMInterface:
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def query(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {e}"
EOF

# --- Install dependencies ---
echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install python-telegram-bot==20.6 openai==1.30.5 python-dotenv httpx==0.27.0 httpcore==1.0.5 anyio==3.7.1

echo "=== Build Complete ==="
echo "Structure ready under $(pwd)"
