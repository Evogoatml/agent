import os, requests

class LLMInterface:
    def __init__(self, model = "tinydolphin:1.1b"):
        self.model = model
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    def query(self, prompt):
        try:
            response = requests.post(self.ollama_url, json={"model": self.model, "prompt": prompt}, timeout=60)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return f"❌ Ollama error: {response.text}"
        except Exception as e:
            return f"⚠️ Local LLM connection error: {e}"
