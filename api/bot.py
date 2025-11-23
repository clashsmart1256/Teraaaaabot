import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ←←← TERA KEY DAAL DIYA HAI
RAPIDAPI_KEY = "96d0825ba6msh411be1381868091p1465bejsn8dc0376ddd7c"

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

async def get_terabox_link(link: str):
    url = "https://terabox-downloader-direct-download-link-generator.p.rapidapi.com/api/v1/download"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "terabox-downloader-direct-download-link-generator.p.rapidapi.com"
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, params={"url": link}, timeout=30)
            data = r.json()
            if data.get("success"):
                f = data["data"]
                return {
                    "name": f["file_name"],
                    "size": f["file_size"],
                    "dlink": f["download_link"],
                    "thumb": f.get("thumbnail", "")
                }
    except: pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("TeraBox Bot ON\nLink bhejo → 2 sec mein download ready!")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not ("terabox.com/s/" in text or "1024terabox.com/s/" in text):
        await update.message.reply_text("Sirf TeraBox link bhejo bhai")
        return

    msg = await update.message.reply_text("Link check kar raha…")
    info = await get_terabox_link(text)

    if not info:
        await msg.edit_text("Link expired ya temporarily down — thodi der baad try karo")
        return

    proxy = f"https://teraaaaabot.vercel.app/proxy?url={info['dlink']}&name={info['name']}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Proxy Download (Full Speed)", url=proxy)]
    ])

    caption = f"**{info['name']}**\nSize: `{info['size']}`\n\nDownload shuru kar do!"

    if info['thumb']:
        await msg.delete()
        await update.message.reply_photo(info['thumb'], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

async def init_bot():
    if not bot_app.running:
        await bot_app.initialize()
        await bot_app.start()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

@app.post("/webhook")
async def webhook(request: Request):
    await init_bot()
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "file"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url)
        return Response(content=r.content, media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

@app.get("/")
async def home():
    return {"status": "Bot Live with RapidAPI"}
