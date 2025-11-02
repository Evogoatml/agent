import aiohttp
import asyncio
import json
import os
import time
from core.memory_core import memory_core
from core.key_store import key_store
# ...
auth_key = key_store.get(api.get("auth_key_env", api.get("auth_key", "")))


REGISTRY_PATH = "data/api_registry.json"

class APIManager:
    def __init__(self):
        self.registry = self.load_registry()

    def load_registry(self):
        if not os.path.exists(REGISTRY_PATH):
            raise FileNotFoundError(f"Missing {REGISTRY_PATH}")
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)

    async def _fetch(self, session, method, url, headers=None, payload=None):
        start = time.time()
        try:
            async with session.request(method, url, headers=headers, json=payload, timeout=15) as resp:
                text = await resp.text()
                duration = round(time.time() - start, 4)
                memory_core.log_execution("api_manager", url, [], {}, text, duration, "OK")
                return {"status": resp.status, "response": text}
        except Exception as e:
            duration = round(time.time() - start, 4)
            memory_core.log_execution("api_manager", url, [], {}, str(e), duration, "ERROR")
            return {"status": "error", "error": str(e)}

    async def execute(self, name, endpoint=None, params=None, payload=None):
        if name not in self.registry:
            return {"error": f"API '{name}' not found in registry"}

        api = self.registry[name]
        base_url = api["base_url"].rstrip("/")
        auth_type = api.get("auth_type", "none")
        auth_key = os.getenv(api.get("auth_key_env", ""), api.get("auth_key", ""))
        method = api.get("method", "GET").upper()
        headers = api.get("headers", {}).copy()
        endpoints = api.get("endpoints", {})

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth_key}"
        elif auth_type == "apikey":
            if "{auth_key}" in base_url:
                base_url = base_url.replace("{auth_key}", auth_key)
            for k in endpoints:
                endpoints[k] = endpoints[k].replace("{auth_key}", auth_key)

        if endpoint not in endpoints:
            endpoint_template = next(iter(endpoints.values()))
        else:
            endpoint_template = endpoints[endpoint]

        if params:
            for k, v in params.items():
                endpoint_template = endpoint_template.replace(f"{{{k}}}", str(v))

        url = f"{base_url}{endpoint_template}"

        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, method, url, headers=headers, payload=payload)

    async def run_many(self, tasks):
        async with aiohttp.ClientSession() as session:
            coros = []
            for task in tasks:
                name, endpoint, params = task
                if name not in self.registry:
                    continue
                api = self.registry[name]
                base_url = api["base_url"].rstrip("/")
                endpoints = api.get("endpoints", {})
                endpoint_template = endpoints.get(endpoint, next(iter(endpoints.values())))
                for k, v in params.items():
                    endpoint_template = endpoint_template.replace(f"{{{k}}}", str(v))
                url = f"{base_url}{endpoint_template}"
                coros.append(self._fetch(session, api.get("method", "GET"), url))
            return await asyncio.gather(*coros)

api_manager = APIManager()
