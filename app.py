import os
import uvicorn
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from queue import Queue
import threading
from core.orchestrator_secure import OrchestratorSecure
from core.memory_core import memory_core
from core.bootstrap import init_runtime
init_runtime()

app = FastAPI(title="ADAP Agent API", version="2.0")

orch = OrchestratorSecure()
orch.auto_discover()
task_queue = Queue()

def worker():
    while True:
        job = task_queue.get()
        if job is None:
            break
        try:
            start = time.time()
            res = orch.execute(**job)
            dur = time.time() - start
            memory_core.log_execution(job["module_name"], job["func_name"], job["args"], job["kwargs"], res, dur, "OK")
        except Exception as e:
            dur = time.time() - start
            memory_core.log_execution(job["module_name"], job["func_name"], job["args"], job["kwargs"], str(e), dur, "ERR")
        task_queue.task_done()

for _ in range(2):
    threading.Thread(target=worker, daemon=True).start()

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

@app.get("/")
def root():
    return {
        "status": "running",
        "modules": orch.list_modules(),
        "feedback": memory_core.get_feedback(limit=3)
    }

@app.get("/modules/{name}")
def inspect_module(name: str):
    funcs = orch.inspect_module(name)
    if funcs is None:
        raise HTTPException(404, f"Module '{name}' not found")
    return {"module": name, "functions": funcs}

@app.post("/exec")
def execute(req: ExecRequest):
    try:
        start = time.time()
        result = orch.execute(req.module, req.function, *(req.args or []), **(req.kwargs or {}))
        duration = time.time() - start
        memory_core.log_execution(req.module, req.function, req.args, req.kwargs, result, duration, "OK")
        return {"ok": True, "result": result}
    except Exception as e:
        duration = time.time() - start
        memory_core.log_execution(req.module, req.function, req.args, req.kwargs, str(e), duration, "ERR")
        raise HTTPException(400, str(e))

@app.post("/enqueue")
def enqueue(req: EnqueueRequest):
    task_queue.put({
        "module_name": req.module,
        "func_name": req.function,
        "args": req.args or [],
        "kwargs": req.kwargs or {}
    })
    return {"ok": True, "queued": True}

@app.get("/feedback")
def get_feedback():
    return {"feedback": memory_core.get_feedback(limit=10)}

if __name__ == "__main__":
    os.environ["PYTHONPATH"] = "."
    uvicorn.run(app, host="0.0.0.0", port=7861)
