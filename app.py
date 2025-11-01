import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
LLM_ENDPOINT = os.getenv(
    "LLM_ENDPOINT",
    "https://api-inference.huggingface.co/models/DavidAU/Qwen3-MOE-6x0.6B-3.6B-Writing-On-Fire-Uncensored"
)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "🤖 AI Agent Webhook Active", 200

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "ok", 200

    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "")

    if text == "/start":
        send_message(chat_id, "🔥 Qwen3-MOE AI ready. Send me any text to generate a response.")
    else:
        response = query_llm(text)
        send_message(chat_id, response)

    return "ok", 200


def query_llm(prompt: str) -> str:
    """Query the Hugging Face Inference API."""
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        res = requests.post(
            LLM_ENDPOINT,
            headers=headers,
            json={"inputs": prompt},
            timeout=60
        )

        if not res.ok:
            return f"⚠️ API error: {res.status_code} - {res.text}"

        data = res.json()
        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return data[0]["generated_text"]
        elif isinstance(data, dict) and "error" in data:
            return f"⚠️ HF error: {data['error']}"
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Connection error: {e}"


def send_message(chat_id: int, text: str):
    """Send a message back to Telegram."""
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
