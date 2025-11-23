from fastapi import FastAPI, Request, Response
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import re
import httpx

app = FastAPI()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

# Simple in-memory storage
user_links = {}

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

async def get_terabox_links(link: str, cookie: str):
    cookie = cookie.strip()
    if not cookie.startswith("ndus="):
        cookie = "ndus=" + cookie

    match = re.search(r"/s/([a-zA-Z0-9]+)", link)
    if not match:
        return None, "Invalid TeraBox link"

    shortcode = match.group(1)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Step 1: Get file info
            r1 = await client.post(
                "https://www.1024terabox.com/share/list",
                data={"shorturl": shortcode},
                headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"}
            )
            data = r1.json()
            if data.get("errno") != 0:
                return None, "Invalid or expired cookie"

            file = data["list"][0]
            fs_id = file["fs_id"]
            shareid = data["shareid"]
            uk = data["uk"]

            # Step 2: Get direct link
            r2 = await client.post(
                "https://www.1024terabox.com/api/download",
                json={"shareid": shareid, "uk": uk, "fstype": "1", "fs_ids": [fs_id], "type": "nolimit"},
                headers={"Cookie": cookie}
            )
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Failed to generate download link"

            dlink = res["dlink"][0]["dlink"]
            proxy_url = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={file['server_filename']}"

            return {
                "name": file["server_filename"],
                "size": format_size(int(file["size"])),
                "thumb": file.get("thumbs", {}).get("url3", ""),
                "direct": dlink,
                "proxy": proxy_url
            }, None

        except:
            return None, "Network error, try again"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Downloader Bot\n\n"
        "Send me any TeraBox share link\n"
        "I'll ask for your NDUS cookie → give you direct + proxy links!\n\n"
        "@login12345bot"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # User sent a link
    if "terabox.com/s/" in text or "1024terabox.com/s/" in text:
        user_links[user_id] = text
        await update.message.reply_text(
            "Link received!\n\nNow reply with your **NDUS cookie** (from terabox.com → F12 → Cookies → ndus=...)"
        )

    # User replied with cookie
    elif user_id in user_links:
        link = user_links.pop(user_id)
        await update.message.reply_text("Processing your file...")

        result, error = await get_terabox_links(link, text)
        if error:
            await update.message.reply_text(f"Error: {error}")
            return

        caption = f"**{result['name']}**\nSize: `{result['size']}`\n\nChoose link:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=result["direct"])],
            [InlineKeyboardButton("Proxy Link (Recommended)", url=result["proxy"])]
        ])

        if result["thumb"]:
            await update.message.reply_photo(result["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/proxy")
async def proxy(url: str, name: str = "download"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )

@app.get("/")
async def root():
    return {"message": "TeraBox bot @login12345bot is running!"}
