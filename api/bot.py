import os
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = FastAPI()

# ←←← PUT YOUR TOKEN HERE FOR 100 % SURE IT WORKS (remove again later)
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

application = Application.builder().token(TOKEN).concurrent_updates(True).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("IT WORKS! Bot is finally alive!")

application.add_handler(CommandHandler("start", start))

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("RECEIVED:", data)                 # ← This line will appear in Vercel logs
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        print("PROCESSED update_id:", update.update_id)
    except Exception as e:
        print("ERROR:", str(e))
    return Response(content="OK", status_code=200)

@app.get("/")
async def root():
    return {"status": "Bot is running"}
