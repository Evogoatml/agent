import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Load secrets
load_dotenv('/etc/secrets/.env')

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "ok", 200

    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "")

    if text == "/start":
        send_message(chat_id, "🤖 Bot online and ready.")
    else:
        send_message(chat_id, f"You said: {text}")

    return "ok", 200

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
