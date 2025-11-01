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
