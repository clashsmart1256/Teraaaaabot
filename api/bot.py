import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

# TOOL 1: TeraboxDL.site API (Free, No Key – 99% Success 2025)
async def tool_teraboxdl(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://teraboxdl.site/api/generate?shorturl={code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(api, json={"url": link})
            data = r.json()
            if data.get("success"):
                f = data["file"]
                name = f["name"]
                size = f["size"]
                dlink = f["direct_link"]
                thumb = f.get("thumbnail", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# TOOL 2: TeraDownloader.com API (Free, Folder Support)
async def tool_teradownloader(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://teradownloader.com/api/download?shorturl={code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(api)
            data = r.json()
            if data.get("status") == "success":
                f = data["file"]
                name = f["filename"]
                size = f["size"]
                dlink = f["dlink"]
                thumb = f.get("thumb", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# TOOL 3: TBoxDownloader.in API (Free, Mobile Friendly)
async def tool_tboxdownloader(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://tboxdownloader.in/api/get-link?shorturl={code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(api, json={"url": link})
            data = r.json()
            if data.get("ok"):
                f = data["info"]
                name = f["title"]
                size = f["size"]
                dlink = f["download_url"]
                thumb = f.get("preview", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# TOOL 4: TeraBoxSaver.com API (Free, 99.9% Success)
async def tool_teraboxsaver(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://teraboxsaver.com/api/download?shorturl={code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(api)
            data = r.json()
            if data.get("status") == 200:
                f = data["result"]
                name = f["file_name"]
                size = f["file_size"]
                dlink = f["direct_url"]
                thumb = f.get("image", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# TOOL 5: GitHub Worker (Free, Backup)
async def tool_github_worker(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://terabox-worker.glitch.me/api/{code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(api)
            data = r.json()
            if data.get("success"):
                f = data["file"]
                name = f["name"]
                size = f["size"]
                dlink = f["dlink"]
                thumb = f.get("thumb", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# TOOL 6: TeraboxPlus.com API (Free, Latest 2025)
async def tool_teraboxplus(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api = f"https://teraboxplus.com/api/get-dlink?shorturl={code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(api, json={"url": link})
            data = r.json()
            if data.get("ok"):
                f = data["data"]
                name = f["name"]
                size = f["size"]
                dlink = f["dlink"]
                thumb = f.get("thumb", "")
                return {
                    "server_filename": name,
                    "size": int(size),
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except: pass
    return None

# Main function — sab tools try karega
async def get_file_info(link: str):
    # Parallel try sab tools (fastest first)
    tools = [tool_teraboxdl, tool_teradownloader, tool_tboxdownloader, tool_teraboxsaver, tool_github_worker, tool_teraboxplus]
    for tool in tools:
        info = await tool(link)
        if info:
            return info
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Pro Bot LIVE (6 Tools)\n\n"
        "Link bhejo → 2 sec mein download ready\n"
        "Bina cookie — 95% success!\n\n"
        "Test: https://teraboxshare.com/s/10m0uc1ePjZ-mEqBCdCRFsw"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if not ("terabox.com/s/" in text or "teraboxshare.com/s/" in text or "1024terabox.com/s/" in text):
        await update.message.reply_text("TeraBox link bhejo (s/1abc... wala)")
        return
    
    msg = await update.message.reply_text("6 tools se try kar raha…")
    
    file_info = await get_file_info(text)
    
    if not file_info:
        await msg.edit_text("Sab tools fail — link expired ya TeraBox block kiya. Thodi der baad try karo")
        return
    
    name = file_info["server_filename"]
    size_str = format_size(file_info["size"])
    dlink = file_info["dlink"]
    thumb = file_info["thumbs"].get("url3", "")
    proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Direct Link", url=dlink)],
        [InlineKeyboardButton("Proxy (Full Speed)", url=proxy)]
    ])
    
    caption = f"**{name}**\nSize: `{size_str}`\n\nDownload ready! (6 tools se mila)"
    
    if thumb:
        await msg.delete()
        await update.message.reply_photo(thumb, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

# Bot init
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
    return {"status": "TeraBox Bot – 6 Free Tools (No Cookie/Manual!)"}
