import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

# ये दो dict जरूरी हैं — मैं भूल गया था define करना!
user_links = {}   # user_id → link (जब तक cookie न आए)
user_cookies = {} # user_id → ndus cookie (permanent save)

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

# TeraBox से direct link निकालने वाला फंक्शन (cookie के साथ)
async def get_direct_link(link: str, cookie: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        headers = {"Cookie": cookie, "User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(headers=headers, timeout=40) as client:
            # Step 1: Share list
            r1 = await client.get(f"https://www.terabox.com/share/list?app_id=250528&shorturl={code}")
            data = r1.json()
            if data.get("errno") != 0:
                return None, "Cookie expired ya galat hai"
            file = data["list"][0]

            # Step 2: Direct download link
            payload = {
                "shareid": data["shareid"],
                "uk": data["uk"],
                "primaryid": data["shareid"],
                "fid_list": [file["fs_id"]]
            }
            r2 = await client.post("https://www.terabox.com/api/download", json=payload)
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Download link generate nahi hua"
            
            dlink = res["dlink"][0]["dlink"]
            name = file["server_filename"]
            size = int(file["size"])
            thumb = file.get("thumbs", {}).get("url3", "")
            proxy = f"https://teraaaaabot.vercel.app/proxy?url={dlink}&name={name}"
            
            return {
                "name": name,
                "size": size,
                "dlink": dlink,
                "thumb": thumb,
                "proxy": proxy
            }, None
    except Exception as e:
        return None, f"Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TeraBox Downloader Bot LIVE\n\n"
        "1. TeraBox link bhejo\n"
        "2. ndus= cookie bhejo (ek baar)\n"
        "3. Download link mil jayega!\n\n"
        "Cookie kaise nikale? → terabox.com login → F12 → Application → Cookies → ndus= copy"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # अगर लिंक है
    if re.search(r"terabox\.com/s/|1024terabox\.com/s/|teraboxshare\.com/s/", text):
        user_links[user_id] = text
        await update.message.reply_text(
            "Link save kar liya!\n\n"
            "Ab ndus= cookie bhejo (jaise: ndus=AAHBc8dEfG...)\n"
            "Ek baar daalne ke baad hamesha kaam karega!"
        )
        return

    # अगर cookie भेजा है (पहले लिंक भेजा था)
    if user_id in user_links:
        link = user_links.pop(user_id)  # लिंक निकाल लिया
        cookie = text.strip()
        if not cookie.startswith("ndus="):
            cookie = "ndus=" + cookie

        # Cookie save कर लिया user के लिए
        user_cookies[user_id] = cookie

        msg = await update.message.reply_text("Cookie save kiya! Ab link process kar raha…")

        info, err = await get_direct_link(link, cookie)
        if err:
            await msg.edit_text(f"Error: {err}\n\nFresh cookie daal do")
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["dlink"])],
            [InlineKeyboardButton("Proxy Download (Full Speed)", url=info["proxy"])]
        ])

        caption = f"**{info['name']}**\nSize: `{format_size(info['size'])}`\n\nDownload ready bhai!"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        return

    # अगर पहले से cookie save है तो direct process करो
    if user_id in user_cookies and re.search(r"terabox\.com/s/|1024terabox\.com/s/|teraboxshare\.com/s/", text):
        msg = await update.message.reply_text("Cookie pehle se hai! Process kar raha…")
        info, err = await get_direct_link(text, user_cookies[user_id])
        if err:
            await msg.edit_text(f"Cookie expired ho gaya: {err}\n\nNaya cookie bhejo")
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link", url=info["dlink"])],
            [InlineKeyboardButton("Proxy Download", url=info["proxy"])]
        ])

        caption = f"**{info['name']}**\nSize: `{format_size(info['size'])}`\n\nDownload shuru kar do!"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        return

    await update.message.reply_text("Pehle TeraBox link bhejo!")

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
    return {"status": "TeraBox Bot 100% Working with Cookie Save"}
