import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"
app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

user_links = {}
user_cookies = {}  # user_id → cookies dict (from txt)

def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def parse_cookies_txt(txt: str) -> dict:
    cookies = {}
    for line in txt.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name, value = parts[-2], parts[-1]
            cookies[name] = value
    return cookies

async def get_direct_link(link: str, cookies: dict):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.1024terabox.com/",
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())
        }

        async with httpx.AsyncClient(headers=headers, timeout=60, follow_redirects=True) as client:
            # Share list
            r1 = await client.get(f"https://www.1024terabox.com/share/list?app_id=250528&shorturl={code}&root=1")
            data = r1.json()
            if data.get("errno") != 0:
                return None, f"Cookie expired ya invalid! errno: {data.get('errno')}\nNaya cookies.txt upload kar."

            file = data["list"][0]
            payload = {
                "shareid": data["shareid"],
                "uk": data["uk"],
                "primaryid": data["shareid"],
                "fid_list": [file["fs_id"]]
            }
            r2 = await client.post("https://www.1024terabox.com/api/download", json=payload)
            res = r2.json()
            if res.get("errno") != 0:
                return None, f"Download failed! errno: {res.get('errno')}"

            dlink = res["dlink"][0]["dlink"]
            name = file["server_filename"]
            size = int(file["size"])
            thumb = file.get("thumbs", {}).get("url3", "")
            proxy = f"https://teraaaaabot.vercel.app/proxy?url={quote(dlink)}&name={quote(name)}"

            return {"name": name, "size": size, "dlink": dlink, "thumb": thumb, "proxy": proxy}, None

    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("TeraBox Bot LIVE!\n\n1. cookies.txt upload kar (Netscape format)\n2. Link bhejo → direct + proxy milega!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if re.search(r"1024terabox\.com/s/|terabox\.com/s/", text):
        if user_id not in user_cookies:
            user_links[user_id] = text
            await update.message.reply_text("Link save kiya!\nAb cookies.txt upload kar do (document mein)")
            return

        msg = await update.message.reply_text("Processing...")
        info, err = await get_direct_link(text, user_cookies[user_id])
        if err:
            await msg.edit_text(err)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["dlink"])],
            [InlineKeyboardButton("Proxy Full Speed", url=info["proxy"])]
        ])
        caption = f"**{info['name']}**\nSize: `{format_size(info['size'])}`\n\nDownload kar bhai!"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    if doc.file_name and doc.file_name.endswith(".txt"):
        file = await doc.get_file()
        content = await file.download_as_bytearray()
        txt = content.decode()
        parsed = parse_cookies_txt(txt)
        if "ndus" not in parsed:
            await update.message.reply_text("Invalid cookies.txt! ndus missing")
            return
        user_cookies[user_id] = parsed
        await update.message.reply_text("Cookies save ho gaya! Ab link daal")
        if user_id in user_links:
            link = user_links.pop(user_id)
            fake_update = Update.de_json({"update_id": 999, "message": {"text": link, "chat": {"id": user_id}, "from_user": {"id": user_id}}}, bot_app.bot)
            await handle_text(fake_update, context)

# Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))

@app.on_event("startup")
async def start_bot():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"https://teraaaaabot.vercel.app/{TOKEN}"
    )

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
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
            headers={"Content-Disposition": f'attachment; filename="{quote(name)}"'}
        )

@app.get("/")
async def home():
    return {"status": "TeraBox Bot LIVE – No requests, No lauda!"}
