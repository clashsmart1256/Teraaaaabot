import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

# Apna Bot Token Daal
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

# User → ndus cookie string
user_cookies = {}
user_links = {}

def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

async def get_direct_link(link: str, ndus_cookie: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.terabox.com/",
            "Cookie": ndus_cookie,                     # Sirf ndus= chahiye!
            "Accept": "application/json, text/plain, */*"
        }

        async with httpx.AsyncClient(headers=headers, timeout=60) as client:
            # Step 1: Share list
            r1 = await client.get(f"https://www.terabox.com/share/list?app_id=250528&shorturl={code}&pwd=&root=1")
            data = r1.json()

            if data.get("errno") != 0:
                return None, f"Cookie expired ya invalid! errno: {data.get('errno')}\nNaya ndus= daal."

            file = data["list"][0]

            # Step 2: Download API (nolimit = bade files ke liye magic)
            payload = {
                "shareid": data["shareid"],
                "uk": data["uk"],
                "primaryid": data["shareid"],
                "fid_list": [file["fs_id"]],
                "type": "nolimit",        # YE LINE BADE FILES KE LIYE ZAROORI HAI
                "product": "share"
            }

            r2 = await client.post("https://www.terabox.com/api/download", json=payload)
            res = r2.json()

            if res.get("errno") != 0:
                return None, f"Download link nahi mila! errno: {res.get('errno')}"

            dlink = res["dlink"][0]["dlink"]
            name = file["server_filename"]
            size = int(file["size"])
            thumb = file.get("thumbs", {}).get("url3", "")

            proxy_url = f"https://teraaaaabot.vercel.app/proxy?url={quote(dlink)}&name={quote(name)}"

            return {
                "name": name,
                "size": size,
                "dlink": dlink,
                "thumb": thumb,
                "proxy": proxy_url
            }, None

    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Downloader Bot LIVE (200GB+ Full Speed)\n\n"
        "1. Sirf ndus= cookie paste kar → terabox.com login > F12 > Application > Cookies > ndus= copy\n"
        "2. TeraBox link bhejo → direct + proxy milega!\n\n"
        "Ek baar ndus= daala → 30-60 din chalega!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Cookie detect (sirf ndus=)
    if text.startswith("ndus="):
        user_cookies[user_id] = text.strip()
        await update.message.reply_text("Cookie save ho gaya! Ab link daal bhai")
        # Agar pehle link bheja tha to process kar
        if user_id in user_links:
            link = user_links.pop(user_id)
            update.message.text = link
            await handle_message(update, context)
        return

    # Link detect
    if re.search(r"terabox\.com/s/|1024terabox\.com/s/|teraboxapp\.com/s/", text):
        if user_id not in user_cookies:
            user_links[user_id] = text
            await update.message.reply_text("Link save kiya!\nAb sirf ndus= cookie paste kar")
            return

        msg = await update.message.reply_text("Processing link...")

        info, err = await get_direct_link(text, user_cookies[user_id])
        if err:
            await msg.edit_text(err)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["dlink"])],
            [InlineKeyboardButton("Proxy (Full Speed + Resume)", url=info["proxy"])]
        ])

        caption = f"**{info['name']}**\nSize: `{format_size(info['size'])}`\n\nDownload shuru kar do bhai!"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        return

    await update.message.reply_text("Sirf ndus= cookie paste kar ya TeraBox link bhejo!")

# Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"https://teraaaaabot.vercel.app/{TOKEN}"  # Apna domain daal
    )

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "download.mp4"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{quote(name)}"'}
        )

@app.get("/")
async def home():
    return {"status": "TeraBox Bot 100% LIVE – Sirf ndus= cookie – 200GB+ Full Speed!"}
