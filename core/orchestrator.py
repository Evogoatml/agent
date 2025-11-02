import importlib
import inspect
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

class Orchestrator:
    def __init__(self):
        self.registry = {}

    def register(self, name: str, path: str):
        try:
            module = importlib.import_module(path)
            self.registry[name] = module
            logging.info(f"Registered module: {name} -> {path}")
        except Exception as e:
            logging.error(f"Failed to register {name}: {e}")

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

    def execute(self, module_name: str, func_name: str, *args, **kwargs):
        module = self.registry.get(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not registered.")
        func = getattr(module, func_name, None)
        if not callable(func):
            raise ValueError(f"Function '{func_name}' not found in '{module_name}'.")
        logging.info(f"Executing {module_name}.{func_name}")
        return func(*args, **kwargs)

    def list_modules(self):
        return list(self.registry.keys())

    def inspect_module(self, module_name: str):
        module = self.registry.get(module_name)
        if not module:
            return None
        return [m[0] for m in inspect.getmembers(module, inspect.isfunction)]


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.auto_discover()

    # Example usage
    print("Loaded modules:", orchestrator.list_modules())

    # Run an example function if it exists
    # result = orchestrator.execute("crypto_module", "encrypt", "data")
    # print(result)
