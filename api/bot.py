import os
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

app = FastAPI()

# Put your token directly here for testing (remove later and use Vercel env var)
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"  # ← change only if you regenerate

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is alive! Webhook working perfectly")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# Health check
@app.get("/")
def home():
    return {"message": "TeraBox bot webhook ready"}
