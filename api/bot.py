import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ←←← APNA TOKEN YAHAN DAAL DO
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

links = {}  # user_id → link

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

async def get_direct_link(link: str, cookie: str):
    if not cookie.startswith("ndus="):
        cookie = "ndus=" + cookie.strip()
    m = re.search(r"/s/([a-zA-Z0-9_-]+)", link)
    if not m: return None, "Invalid link"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://www.1024terabox.com/share/list",
                data={"shorturl": m.group(1)},
                headers={"Cookie": cookie}
            )
            data = r.json()
            if data.get("errno") != 0: return None, "Cookie galat ya expired"
            file = data["list"][0]
            dlink = file["dlink"]
            proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={file['server_filename']}"
            return {
                "name": file["server_filename"],
                "size": format_size(int(file["size"])),
                "thumb": file.get("thumbs", {}).get("url3", ""),
                "direct": dlink,
                "proxy": proxy
            }, None
    except:
        return None, "Network error"

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("TeraBox Bot LIVE on Vercel\nLink bhejo → ndus cookie bhejo → download ready!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if "terabox.com/s/" in text or "1024terabox.com/s/" in text:
        links[user_id] = text
        await update.message.reply_text("Link saved!\n\nAb ndus= cookie bhejo")
        return

    if user_id in links:
        link = links.pop(user_id)
        msg = await update.message.reply_text("Processing…")
        info, err = await get_direct_link(link, text)
        if err:
            await msg.edit_text(f"{err}")
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["direct"])],
            [InlineKeyboardButton("Proxy (Recommended)", url=info["proxy"])]
        ])
        caption = f"**{info['name']}**\nSize: `{info['size']}`"
        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "file"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.get(url)
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )

@app.get("/")
async def home():
    return {"message": "Bot is running!"}
