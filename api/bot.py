import os
import re
import httpx
from fastapi import Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# ←←← YE TEENO LINES ADD KAR DO (yehi missing thi)
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Token
TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = Application.builder().token(TOKEN).build()
links = {}

def format_size(size):
    size = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

async def get_link(link: str, cookie: str):
    if not cookie.startswith("ndus="): cookie = "ndus=" + cookie.strip()
    code = re.search(r"/s/([a-zA-Z0-9_-]+)", link)
    if not code: return None, "Invalid link"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://www.1024terabox.com/share/list",
                data={"shorturl": code.group(1)},
                headers={"Cookie": cookie}
            )
            data = r.json()
            if data.get("errno") != 0: return None, "Cookie expired ya galat"

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("TeraBox Bot LIVE on Vercel\nLink bhejo → ndus cookie → download ready!")

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    txt = update.message.text.strip()

    if "terabox.com/s/" in txt or "1024terabox.com/s/" in txt:
        links[user] = txt
        await update.message.reply_text("Link saved!\n\nAb ndus= cookie bhejo")
        return

    if user in links:
        link = links.pop(user)
        msg = await update.message.reply_text("Processing…")
        info, err = await get_link(link, txt)
        if err:
            await msg.edit_text(f"{err}")
            return

        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["direct"])],
            [InlineKeyboardButton("Proxy (Best)", url=info["proxy"])]
        ])
        caption = f"**{info['name']}**\nSize: `{info['size']}`"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=btns, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=btns, parse_mode="Markdown")

# ←←← Handlers ab add ho jayenge
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), app.bot)
    await app.process_update(update)
    return Response(status_code=200)

@app.get("/proxy")
async def proxy(url: str, name: str = "file"):
    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as c:
        r = await c.get(url)
        return Response(
            content=r.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{name}"'}
        )

@app.get("/")
async def home():
    return {"status": "Bot Live!"}
