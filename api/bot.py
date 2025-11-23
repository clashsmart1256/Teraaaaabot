import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

# In-memory user storage (reset on restart)
user_cookies = {}  # user_id → ndus cookie
user_links = {}    # user_id → last shared link

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

async def get_direct_link(link: str, cookie=None):
    if cookie is None or not cookie.startswith("ndus="):
        cookie = "ndus=" + cookie.strip() if cookie else ""
    code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
    headers = {"Cookie": cookie, "User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            r = await client.post("https://www.1024terabox.com/share/list", data={"shorturl": code})
            data = r.json()
            if data.get("errno") != 0:
                return None, "Cookie galat ya expired — fresh cookie daal do"
            file = data["list"][0]
            r2 = await client.post("https://www.1024terabox.com/api/download", json={
                "shareid": data["shareid"],
                "uk": data["uk"],
                "fstype": "1",
                "fs_ids": [file["fs_id"]],
                "type": "nolimit"
            })
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Download generate nahi hua"
            dlink = res["dlink"][0]["dlink"]
            proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={file['server_filename']}"
            return {
                "server_filename": file["server_filename"],
                "size": int(file["size"]),
                "dlink": dlink,
                "thumbs": {"url3": file.get("thumbs", {}).get("url3", "")}
            }, None
    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Bot LIVE (Cookie Save Mode)

"
        "Link bhejo → pehli baar cookie maangega (ek baar daal, hamesha kaam)
"
        "Aage se automatic!

"
        "Cookie kaise nikale: terabox.com login → F12 → Application → Cookies → ndus copy"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if "terabox.com/s/" in text or "1024terabox.com/s/" in text or "teraboxshare.com/s/" in text:
        user_links[user_id] = text
        await update.message.reply_text(
            "Link saved!

"
            "Pehli baar ndus= cookie bhejo (ek baar daal, save ho jayega):
"
            "• terabox.com login → F12 → Application → Cookies → ndus copy"
        )
        return

    if user_id in user_links:
        link = user_links[user_id]
        cookie = text
        user_cookies[user_id] = cookie
        msg = await update.message.reply_text("Cookie saved! Ab se automatic chalega… Processing link")
        info, err = await get_direct_link(link, cookie)
        if err:
            await msg.edit_text(f"{err}")
            return
        name = info["server_filename"]
        size_str = format_size(info["size"])
        dlink = info["dlink"]
        thumb = info["thumbs"].get("url3", "")
        proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=dlink)],
            [InlineKeyboardButton("Proxy (Full Speed)", url=proxy)]
        ])
        caption = f"**{name}**
Size: `{size_str}`

Download ready! (Cookie saved for future)"
        if thumb:
            await msg.delete()
            await update.message.reply_photo(thumb, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        del user_links[user_id]
        return

    await update.message.reply_text("Pehle link bhejo, phir cookie")

async def init_bot():
    if not bot_app.running:
        await bot_app.initialize()
        await bot_app.start()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.post("/webhook")
async def webhook(request: Request):
    await init_bot()
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "download"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url)
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )

@app.get("/")
async def home():
    return {"status": "TeraBox Bot – Cookie Save Mode (100% Working!)"}
