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
