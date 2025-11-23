import os
import json
from fastapi import FastAPI, Request, Response
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = FastAPI()
TOKEN = os.getenv("BOT_TOKEN")  # Uses Vercel env var
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive! Webhook working. Send any text to echo.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

@app.post("/webhook")
async def webhook(request: Request):
    try:
        json_data = await request.json()
        print(f"Received update: {json_data.get('update_id', 'unknown')}")  # Logs to Vercel
        update = Update.de_json(json_data, bot)
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"Error in webhook: {e}")  # Logs to Vercel for debugging
        return Response(status_code=200, content="OK")  # Always return 200 to avoid Telegram retries

@app.get("/")
async def home():
    return {"status": "Echo bot ready – test /start!"}
