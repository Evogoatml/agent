import os, logging, requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docx import Document as Docx
import PyPDF2
import openai

# ----- Setup -----
os.makedirs("data/docs", exist_ok=True)
os.makedirs("logs", exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN") or input("Enter Telegram BOT TOKEN: ").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or input("Enter OpenAI API Key: ").strip()
os.environ["BOT_TOKEN"] = BOT_TOKEN
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai.api_key = OPENAI_API_KEY

logging.basicConfig(filename="logs/bot.log", level=logging.INFO)

# ----- Commands -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot ready. Use /scrape <url>, /summarize <url>, or send a file.")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /scrape <url>")
    url = context.args[0]
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        await update.message.reply_text(text[:4000] or "No text found.")
    except Exception as e:
        await update.message.reply_text(str(e))

async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /summarize <url>")
    url = context.args[0]
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt="Summarize this text:\n" + text[:8000],
            max_tokens=300
        )
        summary = response.choices[0].text.strip()
        await update.message.reply_text(summary[:4000])
    except Exception as e:
        await update.message.reply_text(str(e))

async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return
    file = await document.get_file()
    file_path = f"data/docs/{document.file_name}"
    await file.download_to_drive(file_path)

    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join(p.extract_text() or "" for p in reader.pages)
        elif file_path.endswith(".docx"):
            doc = Docx(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            return await update.message.reply_text("Unsupported file type.")

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt="Summarize this document:\n" + text[:8000],
            max_tokens=300
        )
        summary = response.choices[0].text.strip()
        await update.message.reply_text(summary[:4000])
    except Exception as e:
        await update.message.reply_text(str(e))

# ----- Run -----
from telegram.ext import Application
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scrape", scrape))
    app.add_handler(CommandHandler("summarize", summarize))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_handler))
    print("Bot running...")
    app.run_polling()
