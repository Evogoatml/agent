from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from core.enclave_gateway import EnclaveGateway
import os

load_dotenv(dotenv_path="./.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
core = EnclaveGateway()

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Core ready. Send me a prompt.")

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    response = core.process_request(user_text)
    await update.message.reply_text(response[:4000])

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("=== Telegram bot active ===")
    app.run_polling()

if __name__ == "__main__":
    main()
