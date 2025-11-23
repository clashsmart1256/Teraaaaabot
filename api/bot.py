import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ←←← APNA TOKEN YAHAN HAI
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

# 100% WORKING WITHOUT COOKIE – NOV 2025
async def get_file_info(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        api_url = f"https://terabox-dl.qtcloud.workers.dev/api/get-info?shorturl={code}&locale=en"
        
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.get(api_url)
            data = r.json()
            
            if data.get("ok"):
                f = data["response"]
                name = f["name"]
                size = int(f["size"])
                dlink = f["direct_link"]
                thumb = f.get("thumb", "")
                proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
                
                return {
                    "server_filename": name,
                    "size": size,
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }
    except Exception as e:
        print("API Error:", e)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Pro Bot LIVE\n\n"
        "Bas koi bhi TeraBox/1024terabox link bhejo\n"
        "2 second mein download link mil jayega\n\n"
        "Cookie ki zaroorat nahi – 100% bina cookie!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if not ("terabox.com/s/" in text or "1024terabox.com/s/" in text):
        await update.message.reply_text("TeraBox link bhejo bhai")
        return
    
    msg = await update.message.reply_text("Link check kar raha… 2 sec")
    
    file_info = await get_file_info(text)
    
    if not file_info:
        await msg.edit_text("Link expired ya temporarily down hai\nThodi der baad try karo")
        return
    
    name = file_info["server_filename"]
    size_str = format_size(file_info["size"])
    dlink = file_info["dlink"]
    thumb = file_info["thumbs"].get("url3", "")
    proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Direct Link", url=dlink)],
        [InlineKeyboardButton("Proxy Download (Full Speed)", url=proxy)]
    ])
    
    caption = f"**{name}**\nSize: `{size_str}`\n\nDownload shuru kar do!"
    
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

# Handlers
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
    return {"status": "TeraBox Bot – Zero Cookie Needed!"}
