#!/bin/bash
set -e

echo "=== Initializing AI Agent Environment ==="

# Create structure
mkdir -p core data logs

# Python venv
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install openai python-dotenv python-telegram-bot gradio

# Create .gitignore if missing
cat <<EOF > .gitignore
.env
__pycache__/
venv/
logs/
EOF

# Create controller
cat <<'EOF' > controller.py
from dotenv import load_dotenv
import os
from core.enclave_gateway import EnclaveGateway

load_dotenv(dotenv_path="./.env")
print("=== Environment Loaded ===")
print(f"OpenAI key: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"Bot token: {bool(os.getenv('BOT_TOKEN'))}")

if __name__ == "__main__":
    g = EnclaveGateway()
    print(g.process_request("System test: confirm LLM link is active."))
EOF

# Create core modules
mkdir -p core
cat <<'EOF' > core/llm_interface.py
from openai import OpenAI
import os

class LLMInterface:
    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def respond(self, system, user):
        res = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}]
        )
        return res.choices[0].message.content.strip()
EOF

cat <<'EOF' > core/enclave_gateway.py
from .llm_interface import LLMInterface

class EnclaveGateway:
    def __init__(self, model="gpt-4o-mini"):
        self.llm = LLMInterface(model=model)

    def process_request(self, prompt):
        system_prompt = "You are the secure AI core. Respond clearly and safely."
        return self.llm.respond(system_prompt, prompt)
EOF

echo "=== Setup Complete ==="
python3 controller.py
