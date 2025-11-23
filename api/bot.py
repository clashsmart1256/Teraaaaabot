import re
import requests
from fastapi import FastAPI, Request, Response, UploadFile, File
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote, urlparse, parse_qs
from io import StringIO

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"
app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

user_links = {}
user_cookies_content = {}  # user_id → cookies.txt string

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def parse_netscape_cookies(content: str):
    """Netscape cookies.txt ko dict mein convert"""
    cookies = {}
    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('#') or '\t' not in line:
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            domain, _, path, secure, expiry, name, value = parts[0:7]
            if 'terabox' in domain.lower() or '1024tera' in domain.lower():
                cookies[name] = value
    return cookies

def extract_shortcode(link: str):
    """Link se shortcode nikaal"""
    match = re.search(r'/s/([a-f0-9]{12,})', link)
    if match:
        return match.group(1)
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    return query.get('surl', [None])[0] or query.get('shorturl', [None])[0]

def get_direct_link(link: str, cookies_dict: dict):
    """Direct link generate (sync, requests use)"""
    try:
        shortcode = extract_shortcode(link)
        if not shortcode:
            return None, "Invalid TeraBox link!"

        base_url = "https://www.1024terabox.com"  # Domain match for cookies
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": base_url,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9"
        }

        session = requests.Session()
        session.cookies.update(cookies_dict)
        session.headers.update(headers)

        # Step 1: Share list fetch
        params = {
            "app_id": 250528,
            "channel": "dlink_download",
            "clienttype": 0,
            "shorturl": shortcode,
            "root": 1,
            "pwd": ""
        }
        r1 = session.get(f"{base_url}/share/list", params=params, timeout=30)
        data = r1.json()

        if data.get("errno") != 0:
            return None, f"Cookie issue! Errno: {data.get('errno')}\nNaya cookies.txt upload kar (fresh login se)."

        if not data.get("list"):
            return None, "No files in link! Folder ho to single file try kar."

        file_info = data["list"][0]  # First file (folder ke liye extend kar sakte)

        # Step 2: Download dlink
        payload = {
            "app_id": 250528,
            "channel": "dlink_download",
            "clienttype": 0,
            "js_token": "",  # Optional, agar mile to add
            "shareid": data["shareid"],
            "uk": data["uk"],
            "primaryid": data["shareid"],
            "fid_list": [file_info["fs_id"]]
        }
        r2 = session.post(f"{base_url}/api/download", json=payload, timeout=30)
        res = r2.json()

        if res.get("errno") != 0:
            return None, f"Download fail! Errno: {res.get('errno')}\nVIP ho to premium cookie try kar."

        dlink = res["dlink"][0]["dlink"]
        name = file_info["server_filename"]
        size = int(file_info["size"])
        thumb = file_info.get("thumbs", {}).get("url3", "")
        proxy_url = f"https://teraaaaabot.vercel.app/proxy?url={quote(dlink)}&name={quote(name)}"

        return {
            "name": name,
            "size": size,
            "dlink": dlink,
            "thumb": thumb,
            "proxy": proxy_url
        }, None

    except requests.exceptions.Timeout:
        return None, "TeraBox slow hai, retry kar!"
    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Downloader Bot (@ARTeraBoxOnlinebot Style) LIVE!\n\n"
        "1. cookies.txt upload kar (F12 > Cookie Editor > Export Netscape)\n"
        "2. TeraBox link bhejo\n\n"
        "Full speed direct + proxy milega. Ek baar cookie daal, mahino chalega!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    if re.search(r"(1024tera|tera)box\.com/s/", text):
        if user_id not in user_cookies_content:
            user_links[user_id] = text
            await update.message.reply_text(
                "Link save! Pehle cookies.txt upload kar (Netscape format se)."
            )
            return

        cookies_dict = parse_netscape_cookies(user_cookies_content[user_id])
        if not cookies_dict.get("ndus"):
            await update.message.reply_text("Invalid cookies.txt! ndus missing hai.")
            return

        msg = await update.message.reply_text("Processing... (Full speed mode ON)")
        info, err = get_direct_link(text, cookies_dict)
        if err:
            await msg.edit_text(err)
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Direct Download", url=info["dlink"])],
            [InlineKeyboardButton("🚀 Proxy (Unlimited Speed)", url=info["proxy"])]
        ])
        caption = f"**{info['name']}**\n📏 Size: `{format_size(info['size'])}`\n\nDownload shuru kar bhai! 🔥"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(
                photo=info["thumb"],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        return

    await update.message.reply_text("TeraBox link bhejo ya cookies.txt upload kar!")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    document = update.message.document
    if document.file_name and 'cookie' in document.file_name.lower() and document.file_name.endswith('.txt'):
        file_obj = await context.bot.get_file(document.file_id)
        content = (await file_obj.download_as_bytearray()).decode('utf-8')
        user_cookies_content[user_id] = content
        await update.message.reply_text("✅ Cookies loaded! Ab link bhejo.")
        if user_id in user_links:
            saved_link = user_links.pop(user_id)
            # Fake update for re-process
            fake_update = Update.de_json({
                "update_id": update.update_id + 1,
                "message": {"message_id": update.message.message_id + 1, "text": saved_link, "chat": {"id": user_id}, "from": {"id": user_id}}
            }, context.bot)
            await handle_message(fake_update, context)
    else:
        await update.message.reply_text("Sirf cookies.txt upload kar (Netscape format)!")

# Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
bot_app.add_handler(MessageHandler(filters.Document, handle_document))

@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"https://teraaaaabot.vercel.app/{TOKEN}"
    )
    print("Bot LIVE - @ARTeraBoxOnlinebot Vibes!")

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "file"):
    async with requests.Session() as s:  # Sync for simplicity
        r = s.get(url, stream=True, timeout=300)
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{quote(name)}"',
                "Content-Length": str(len(r.content))
            }
        )

@app.get("/")
async def home():
    return {"status": "TeraBox Bot - Full Speed Mode | Inspired by @ARTeraBoxOnlinebot"}
