import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Load secrets from Render
load_dotenv('/etc/secrets/.env')

# Telegram Bot Token
TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🤖 Bot online and ready.")
        else:
            send_message(chat_id, f"You said: {text}")
    return "ok", 200


def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": text})


@app.route("/healthz")
def health_check():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
