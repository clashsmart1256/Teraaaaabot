import os
import asyncio
import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = FastAPI()

TOKEN = os.getenv("BOT_TOKEN", "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI")  # Fallback for testing
bot = Bot(token=TOKEN)

# Build application
application = Application.builder().token(TOKEN).build()

user_links = {}

def format_size(size: int) -> str:
    size = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

async def get_terabox_links(link: str, cookie: str):
    if not cookie.startswith("ndus="):
        cookie = "ndus=" + cookie.strip()
    match = re.search(r"/s/([a-zA-Z0-9]+)", link)
    if not match:
        return None, "Invalid TeraBox link!"
    shortcode = match.group(1)
    headers = {"Cookie": cookie, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r1 = await client.post("https://www.1024terabox.com/share/list", data={"shorturl": shortcode}, headers=headers)
            data = r1.json()
            if data.get("errno") != 0:
                return None, "Invalid or expired NDUS cookie!"
            file = data["list"][0]
            fs_id = file["fs_id"]
            share_id = data["shareid"]
            uk = data["uk"]
            r2 = await client.post("https://www.1024terabox.com/api/download", json={
                "shareid": share_id, "uk": uk, "fstype": "1", "fs_ids": [fs_id], "type": "nolimit"
            }, headers=headers)
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Failed to generate link."
            dlink = res["dlink"][0]["dlink"]
            proxy_url = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={file['server_filename']}"
            return {
                "name": file["server_filename"],
                "size": format_size(int(file["size"])),
                "thumb": file.get("thumbs", {}).get("url3", ""),
                "direct": dlink,
                "proxy": proxy_url
            }, None
    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 TeraBox Downloader Bot\n\nSend a TeraBox link → I'll ask for NDUS cookie → Get direct & proxy links!\n\n"
        "Example: https://1024terabox.com/s/1abc123\n\n"
        "@login12345bot"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if "terabox.com/s/" in text or "1024terabox.com/s/" in text:
        user_links[user_id] = text
        await update.message.reply_text(
            "✅ Link saved!\n\nReply with your NDUS cookie:\n• Login to terabox.com\n• F12 → Application → Cookies → Copy 'ndus' value"
        )
        return
    if user_id in user_links:
        link = user_links.pop(user_id)
        msg = await update.message.reply_text("🔄 Processing...")
        result, error = await get_terabox_links(link, text)
        if error:
            await msg.edit_text(f"❌ {error}")
            return
        caption = f"**{result['name']}**\nSize: `{result['size']}`\n\nChoose:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=result["direct"])],
            [InlineKeyboardButton("Proxy Link (Recommended)", url=result["proxy"])]
        ])
        if result["thumb"]:
            await msg.delete()
            await update.message.reply_photo(result["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Initialize application on first request (fixes "not initialized" error)
        if not application.bot:
            await application.initialize()
        data = await request.json()
        print("RECEIVED:", data)
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        print("PROCESSED:", update.update_id)
    except Exception as e:
        print("ERROR:", str(e))
    finally:
        # Clean shutdown (optional for serverless)
        await application.shutdown()
    return {"ok": True}

@app.get("/proxy")
async def proxy(url: str, name: str = "download"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url)
        return Response(
            content=r.content,
            status_code=200,
            headers={"Content-Disposition": f'attachment; filename="{name}"', "Content-Type": "application/octet-stream"}
        )

@app.get("/")
async def root():
    return {"status": "Bot ready – send /start!"}
