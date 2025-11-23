import os
import re
import httpx
from fastapi import FastAPI, Request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = FastAPI()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# Temporary user state (user_id → data)
user_data = {}

def format_bytes(b):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024: return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} TB"

async def get_download_links(link: str, cookie: str):
    if not cookie.startswith("ndus="):
        cookie = "ndus=" + cookie

    match = re.search(r"/s/([a-zA-Z0-9]+)", link)
    if not match:
        return None, "Invalid TeraBox link format!"

    shortcode = match.group(1)
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Step 1: Get file info
            r1 = await client.post("https://www.1024terabox.com/share/list",
                data={"shorturl": shortcode},
                headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"})
            data = r1.json()
            if data.get("errno") != 0:
                return None, "Invalid or expired NDUS cookie!"

            file = data["list"][0]
            fs_id = file["fs_id"]
            share_id = data["shareid"]
            uk = data["uk"]

            # Step 2: Generate direct link
            r2 = await client.post("https://www.1024terabox.com/api/download",
                json={"shareid": share_id, "uk": uk, "fstype": "1", "fs_ids": [fs_id], "type": "nolimit"},
                headers={"Cookie": cookie})
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Failed to generate download link."

            dlink = res["dlink"][0]["dlink"]
            base_url = os.getenv("VERCEL_URL", "https://teraaaaabot.vercel.app")
            if not base_url.startswith("http"):
                base_url = "https://" + base_url
            proxy_url = f"{base_url}/proxy?url={dlink}&name={file['server_filename']}"

            return {
                "name": file["server_filename"],
                "size": format_bytes(int(file["size"])),
                "thumb": file.get("thumbs", {}).get("url3", ""),
                "direct": dlink,
                "proxy": proxy_url
            }, None
        except Exception as e:
            return None, f"Error: {str(e)}"

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Downloader Bot\n\n"
        "Send me any TeraBox share link\n"
        "I'll ask for your NDUS cookie (kept private)\n"
        "Get unlimited direct + proxy download links!\n\n"
        "Made with by @grok_xai",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Source Code", url="https://github.com/YourUsername/teraaaaabot")
        ]])
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if "terabox.com/s/" in text or "1024terabox.com/s/" in text:
        user_data[user_id] = {"link": text}
        await update.message.reply_text(
            "Link received!\n\n"
            "Now reply with your **NDUS cookie** (only you see it):\n"
            "→ Open terabox.com → F12 → Application → Cookies → copy value of **ndus**",
            reply_to_message_id=update.message.message_id
        )
    elif user_id in user_data and update.message.reply_to_message:
        cookie = text
        link = user_data[user_id]["link"]
        del user_data[user_id]

        msg = await update.message.reply_text("Processing your link...")

        result, error = await get_download_links(link, cookie)
        if error:
            await msg.edit_text(f"Error: {error}")
            return

        caption = f"**{result['name']}**\nSize: `{result['size']}`\n\nChoose your link:"
        keyboard = [
            [InlineKeyboardButton("Direct Link", url=result["direct"])],
            [InlineKeyboardButton("Proxy Link (Recommended)", url=result["proxy"])]
        ]

        if result["thumb"]:
            await msg.delete()
            await update.message.reply_photo(
                result["thumb"], caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot)
    await application.process_update(update)
    return {"ok": True}

# Proxy download endpoint
@app.get("/proxy")
async def proxy(url: str, name: str = "download.file"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return r.content, 200, {
            "Content-Disposition": f'attachment; filename="{name}"',
            "Content-Type": "application/octet-stream"
        }

@app.get("/")
async def home():
    return {"message": "TeraBox Bot is alive! @teraaaaabot"}
