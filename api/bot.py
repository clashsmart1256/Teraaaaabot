import re
import httpx
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

TOKEN = "5793553240:AAGMn6pkK8SZurzXDuKsf-yygd43V8bt2fI"
app = FastAPI()

bot_app = Application.builder().token(TOKEN).build()

# Ab user se FULL cookie string lega (jaise tune diya tha)
user_cookies = {}  # user_id → full cookie string

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

async def get_direct_link(link: str, cookie: str):
    try:
        code = re.search(r"/s/([a-zA-Z0-9_-]+)", link).group(1)
        headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": "https://www.terabox.com/",
            "Accept": "application/json, text/plain, */*"
        }

        async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
            # Step 1: Share list
            r1 = await client.get(f"https://www.terabox.com/share/list?app_id=250528&shorturl={code}&pwd=&root=1")
            data = r1.json()
            if data.get("errno") != 0:
                return None, f"Cookie expired ya invalid! Naya full cookie daal do.\nError: {data.get('errmsg', 'Unknown')}"

            file = data["list"][0]

            # Step 2: Download API
            payload = {
                "shareid": data["shareid"],
                "uk": data["uk"],
                "primaryid": data["shareid"],
                "fid_list": [file["fs_id"]]
            }
            r2 = await client.post("https://www.terabox.com/api/download", json=payload)
            res = r2.json()
            if res.get("errno") != 0:
                return None, "Download link nahi mila! Cookie check karo."

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
        "TeraBox Downloader Bot ON\n\n"
        "TeraBox link bhejo → main full speed direct + proxy link dunga!\n\n"
        "Pehli baar full cookie daalna padega (10 second ka kaam):\n"
        "terabox.com login → F12 → Application → Cookies → terabox.com → Export → Netscape format → yaha paste kar do\n\n"
        "Ek baar daala to 3-6 mahine chalega!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Agar TeraBox link hai
    if re.search(r"terabox\.com/s/|1024terabox\.com/s/|teraboxapp\.com/s/|terashare\.com/s/", text):
        if user_id not in user_cookies:
            await update.message.reply_text("Link save kiya!\n\nAb full cookie string bhejo (Netscape format ya direct copy-paste):\n\nExample:\n`ndus=abc; TSID=xyz; browserid=123; csrfToken=def; lang=en`")
            user_links[user_id] = text
            return

        msg = await update.message.reply_text("Processing...")
        info, err = await get_direct_link(text, user_cookies[user_id])
        if err:
            await msg.edit_text(f"{err}\n\nNaya cookie daal do bhai")
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Direct Link (Fast)", url=info["dlink"])],
            [InlineKeyboardButton("Proxy Link (Full Speed + Resume)", url=info["proxy"])]
        ])

        caption = f"**{info['name']}**\nSize: `{format_size(info['size'])}`\n\nDownload shuru kar do!"

        if info["thumb"]:
            await msg.delete()
            await update.message.reply_photo(info["thumb"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await msg.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        return

    # Agar cookie bheja hai
    if "ndus=" in text and ("TSID=" in text or "browserid=" in text or "csrfToken=" in text):
        user_cookies[user_id] = text.strip()
        if user_id in user_links:
            link = user_links.pop(user_id)
            await update.message.reply_text("Cookie save kiya! Ab link process kar raha…")
            # Recursively process saved link
            update.message.text = link
            await handle_message(update, context)
        else:
            await update.message.reply_text("Cookie save ho gaya! Ab TeraBox link bhejo.")
        return

    await update.message.reply_text("Bhai TeraBox link ya full cookie string bhejo!")

# Bot handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

user_links = {}

# Webhook setup (Vercel/Render pe perfect chalega)
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
    print("Bot LIVE ho gaya!")

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
    return {"status": "TeraBox Bot 100% Working | Cookie System ON"}
