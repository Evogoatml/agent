import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
LLM_ENDPOINT = "https://api-inference.huggingface.co/models/DavidAU/Qwen3-MOE-6x0.6B-3.6B-Writing-On-Fire-Uncensored"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "🤖 Webhook Online", 200

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return "ok", 200

    if text.strip() == "/start":
        send_message(chat_id, "🔥 Qwen3-MOE AI ready. Send a message to chat.")
    else:
        response = query_llm(text)
        send_message(chat_id, response)

    return "ok", 200


def query_llm(prompt: str) -> str:
    """Send text to Hugging Face model and return output."""
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        res = requests.post(
            LLM_ENDPOINT,
            headers=headers,
            json={"inputs": prompt},
            timeout=90
        )
        if not res.ok:
            return f"⚠️ HF API Error {res.status_code}: {res.text}"

        data = res.json()
        # Debug print in logs
        print("🔍 HF raw response:", data)

        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()

        return "⚠️ Unexpected response format."
    except Exception as e:
        return f"⚠️ Connection error: {e}"


def send_message(chat_id, text):
    """Send a Telegram message."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print("❌ Telegram send error:", e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
