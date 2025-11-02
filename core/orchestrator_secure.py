import importlib
import inspect
import os
import logging
import hashlib
import json
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class OrchestratorSecure:
    def __init__(self, key: bytes = None):
        self.registry = {}
        self.key = key or hashlib.sha256(b"default_orchestrator_key").digest()
        self.log_file = "logs/orchestrator_events.log"
        os.makedirs("logs", exist_ok=True)

    # ------------------ Registry ------------------

    def register(self, name: str, path: str):
        try:
            module = importlib.import_module(path)
            self.registry[name] = {
                "path": path,
                "signature": self.sign(path),
                "timestamp": datetime.utcnow().isoformat()
            }
            self._log(f"Registered: {name} -> {path}")
        except Exception as e:
            self._log(f"Failed to register {name}: {e}", error=True)

    def auto_discover(self, folders=None):
        if folders is None:
            folders = ["plugins", "skills"]
        for folder in folders:
            if not os.path.isdir(folder):
                continue
            for file in os.listdir(folder):
                if file.endswith(".py") and not file.startswith("__"):
                    name = file[:-3]
                    path = f"{folder}.{name}"
                    self.register(name, path)

    # ------------------ Execution ------------------

    def execute(self, module_name: str, func_name: str, *args, **kwargs):
        info = self.registry.get(module_name)
        if not info:
            raise ValueError(f"Module '{module_name}' not registered.")
        path = info["path"]
        signature = info["signature"]
        if not self.verify(path, signature):
            raise ValueError(f"Signature mismatch for {module_name}")
        module = importlib.import_module(path)
        func = getattr(module, func_name, None)
        if not callable(func):
            raise ValueError(f"Function '{func_name}' not found in '{module_name}'.")
        self._log(f"Executing {module_name}.{func_name}")
        result = func(*args, **kwargs)
        return result

    # ------------------ Security ------------------

    def sign(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def verify(self, data: str, signature: str) -> bool:
        return self.sign(data) == signature

    # ------------------ Encryption ------------------

    def encrypt(self, plaintext: str) -> str:
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
        return (iv + ct).hex()

    def decrypt(self, ciphertext_hex: str) -> str:
        raw = bytes.fromhex(ciphertext_hex)
        iv, ct = raw[:16], raw[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ct), AES.block_size).decode()

    # ------------------ Utilities ------------------

    def list_modules(self):
        return list(self.registry.keys())

    def inspect_module(self, module_name: str):
        module = importlib.import_module(self.registry[module_name]["path"])
        return [m[0] for m in inspect.getmembers(module, inspect.isfunction)]

    def _log(self, message, error=False):
        line = f"{datetime.utcnow().isoformat()} :: {'ERROR' if error else 'INFO'} :: {message}"
        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    orch = OrchestratorSecure()
    orch.auto_discover()
    print("Modules:", orch.list_modules())
