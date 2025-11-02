import os
import json
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from core.orchestrator_secure import OrchestratorSecure
from core.event_bus import EventBus
from core.task_queue import TaskQueue
from core.auto_watcher import AutoWatcher
from core.scheduler import Scheduler

app = FastAPI(title="ADAP Orchestrator", version="1.0")

EVENTS = EventBus()
TASKS = TaskQueue(workers=3)
SCHED = Scheduler()
ORCH = OrchestratorSecure()
ORCH.auto_discover()

os.makedirs("logs", exist_ok=True)
LOG_FILE = "logs/orchestrator_events.log"

# ------------- Auto-triggers -------------

def on_code_change():
    ORCH.auto_discover()
    EVENTS.publish("registry/updated", {"modules": ORCH.list_modules()})
    with open(LOG_FILE, "a") as f:
        f.write("AUTO: registry refreshed due to code change\n")

WATCH = AutoWatcher(paths=["plugins", "skills"], on_change=on_code_change, interval=1.5)
WATCH.start()

def heartbeat():
    EVENTS.publish("heartbeat", {"modules": ORCH.list_modules()})
SCHED.add("hb", every_sec=5.0, fn=heartbeat)
SCHED.start()

# ------------- Models -------------

class ExecRequest(BaseModel):
    module: str
    function: str
    args: Optional[List[Any]] = []
    kwargs: Optional[Dict[str, Any]] = {}

class EnqueueRequest(BaseModel):
    module: str
    function: str
    args: Optional[List[Any]] = []
    kwargs: Optional[Dict[str, Any]] = {}
    priority: int = 10

# ------------- Routes -------------

@app.get("/modules")
def list_modules():
    return {"modules": ORCH.list_modules()}

@app.get("/modules/{name}")
def inspect_module(name: str):
    funcs = ORCH.inspect_module(name)
    if funcs is None:
        raise HTTPException(404, f"Module '{name}' not found")
    return {"name": name, "functions": funcs}

@app.post("/exec")
def execute(req: ExecRequest):
    try:
        result = ORCH.execute(req.module, req.function, *(req.args or []), **(req.kwargs or {}))
        return {"ok": True, "result": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(400, str(e))

@app.post("/enqueue")
def enqueue(req: EnqueueRequest):
    def job():
        try:
            ORCH.execute(req.module, req.function, *(req.args or []), **(req.kwargs or {}))
        except Exception:
            pass
    TASKS.put(job, priority=req.priority)
    return {"ok": True, "queued": True}

@app.get("/events/heartbeat")
def manual_heartbeat():
    heartbeat()
    return {"ok": True}

@app.get("/logs")
def tail_logs(lines: int = 200):
    if not os.path.exists(LOG_FILE):
        return {"lines": []}
    with open(LOG_FILE, "r") as f:
        data = f.readlines()[-abs(lines):]
    return {"lines": [x.rstrip("\n") for x in data]}

# ------------- Minimal UI -------------

@app.get("/")
def root():
    return {
        "ui": "OK",
        "endpoints": [
            "GET /modules",
            "GET /modules/{name}",
            "POST /exec",
            "POST /enqueue",
            "GET /events/heartbeat",
            "GET /logs?lines=200"
        ]
    }
