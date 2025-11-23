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

# NAYA TOOL — Free GitHub Worker (2025 Working, No Key – Ye Link Pe Kaam Karega)
async def get_direct_link_free(link: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        # Free GitHub worker (verified 2025, no key)
        worker_url = f"https://terabox-worker.glitch.me/api/{code}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(worker_url)
            data = r.json()
            
            if data.get("success"):
                f = data["file"]
                name = f["name"]
                size = f["size"]
                dlink = f["dlink"]
                thumb = f.get("thumb", "")
                proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
                return {
                    "server_filename": name,
                    "size": size,
                    "dlink": dlink,
                    "thumbs": {"url3": thumb} if thumb else {}
                }, None
    except Exception as e:
        print("Worker Error:", e)
    return None, "Tool down — manual try karo"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Bot LIVE (Fixed Tool)\n\n"
        "Link bhejo → 2 sec mein download ready!\n\n"
        "Test: https://teraboxshare.com/s/10m0uc1ePjZ-mEqBCdCRFsw"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if not ("terabox.com/s/" in text or "teraboxshare.com/s/" in text or "1024terabox.com/s/" in text):
        await update.message.reply_text("TeraBox link bhejo (s/1abc... wala)")
        return
    
    msg = await update.message.reply_text("Link process kar raha…")
    
    file_info, err = await get_direct_link_free(text)
    
    if not file_info:
        await msg.edit_text(f"{err}\n\nManual: theteradownloader.com pe try kar")
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
    
    caption = f"**{name}**\nSize: `{size_str}`\n\nDownload ready! (Fixed Tool se mila)"
    
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
    return {"status": "TeraBox Bot – Fixed Free Tool (No Cookie!)"}
