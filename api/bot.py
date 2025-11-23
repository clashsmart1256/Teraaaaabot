import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()
user_links = {}  # backup for cookie

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

# 1. Bina cookie try
async def try_without_cookie(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.get(f"https://www.terabox.com/share/list?app_id=250528&shorturl={code}&root=1")
            data = r.json()
            if data.get("errno") == 0 and data.get("list"):
                f = data["list"][0]
                return f, None
    except: pass
    return None, "Bina cookie nahi hua"

# 2. Cookie ke saath (100% success)
async def with_cookie(link: str, cookie: str):
    if not cookie.startswith("ndus="): cookie = "ndus=" + cookie.strip()
    code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
    async with httpx.AsyncClient(headers={"Cookie": cookie}, timeout=30) as client:
        r = await client.post("https://www.1024terabox.com/share/list", data={"shorturl": code})
        data = r.json()
        if data.get("errno") == 0:
            return data["list"][0], None
    return None, "Cookie galat"

# Main handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Link bheja
    if "terabox.com/s/" in text or "1024terabox.com/s/" in text:
        msg = await update.message.reply_text("Trying bina cookie…")

        file_info, err = await try_without_cookie(text)
        cookie_needed = False
        if not file_info:
            user_links[user_id] = text
            await msg.edit_text("Bina cookie nahi hua\n\nCookie daal do (optional):")
            return

    # Cookie bheja
    elif user_id in user_links:
        msg = await update.message.reply_text("Cookie ke saath try kar raha…")
        file_info, err = await with_cookie(user_links.pop(user_id), text)
        if not file_info:
            await msg.edit_text("Cookie bhi galat ya link expired")
            return

    else:
        await update.message.reply_text("Pehle TeraBox link bhejo!")
        return

    # Success — file info mil gaya
    name = file_info["server_filename"]
    size_bytes = int(file_info["size"])
    size_str = format_size(size_bytes)
    thumb = file_info.get("thumbs", {}).get("url3", "")
    dlink = file_info["dlink"]
    proxy_url = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Proxy Download (Full Speed)", url=proxy_url)]
    ])

    # 2 GB se chhoti file → Telegram pe upload
    if size_bytes <= 1.9 * 1024 * 1024 * 1024:  # 1.9 GB
        await msg.edit_text("File chhoti hai — Telegram pe upload kar raha…")
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.get(dlink, follow_redirects=True)
        await update.message.reply_document(
            document=r.content,
            filename=name,
            caption=f"{name}\nSize: {size_str}\nUploaded by your bot!",
            reply_markup=keyboard
        )
        await msg.delete()
    else:
        caption = f"**{name}**\nSize: `{size_str}`\n\nBadi file hai → Proxy se download karo (full speed)"
        if thumb:
            await msg.delete()
            await update.message.reply_photo(thumb, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Pro Bot LIVE\n\n"
        "• 2 GB se chhoti file → Telegram mein direct milegi\n"
        "• Badi file → full speed proxy link\n"
        "• 90% links bina cookie ke chalte hain\n\n"
        "Bas link bhejo aur dekho magic!"
    )

async def init_bot():
    if not bot_app.running:
        await bot_app.initialize()
        await bot_app.start()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.post("/webhook")
async def webhook(request: Request):
    await init_bot()
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "download"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as c:
        r = await c.get(url)
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )

@app.get("/")
async def home():
    return {"status": "TeraBox Pro Bot with Upload + Proxy"}
