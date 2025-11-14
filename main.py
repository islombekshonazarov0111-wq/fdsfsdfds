import os
import asyncio
from yt_dlp import YoutubeDL
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_URL = "https://t.me/attackboy_pubgm"
CHANNEL_USERNAME = "@attackboy_pubgm"

TMP_DIR = "tmp_media"
os.makedirs(TMP_DIR, exist_ok=True)

video_opts = {
    "format": "best",
    "outtmpl": os.path.join(TMP_DIR, "%(id)s.%(ext)s"),
    "quiet": True,
    "no_warnings": True,
}

audio_opts = {
    "format": "bestaudio/best",
    "outtmpl": os.path.join(TMP_DIR, "%(id)s.%(ext)s"),
    "quiet": True,
    "no_warnings": True,
    "postprocessors": [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ],
}

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        status = member.status
        return status not in ("left", "kicked")
    except Exception:
        return False

def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔔 Kanalga obuna bo‘lish", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Obuna bo‘ldim — Tekshirish", callback_data="check_subscription")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Link yuboring — men uni video, rasm yoki audio qilib qaytaraman.
"
        "🎵 Musiqa uchun: /music <link>

"
        f"📢 Avval {CHANNEL_USERNAME} kanaliga obuna bo‘ling."
    )

def download_media(url, opts):
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if opts is audio_opts:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info

async def process_and_send_media(msg, context, url, opts, is_audio=False):
    status_msg = await msg.reply_text("⏳ Yuklanmoqda...")
    try:
        loop = asyncio.get_running_loop()
        filename, info = await loop.run_in_executor(None, lambda: download_media(url, opts))

        if not os.path.exists(filename):
            await status_msg.edit_text("⚠️ Fayl topilmadi.")
            return

        title = info.get("title", "Media")
        caption = f"📥 Yuklandi: {title}"

        ext = os.path.splitext(filename)[1].lower()
        with open(filename, "rb") as f:
            if is_audio or ext in [".mp3", ".m4a", ".aac", ".ogg"]:
                await msg.reply_audio(audio=InputFile(f, filename=os.path.basename(filename)), caption=caption)
            elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                await msg.reply_video(video=InputFile(f), caption=caption)
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                await msg.reply_photo(photo=InputFile(f), caption=caption)
            else:
                await msg.reply_document(document=InputFile(f), caption=caption)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Xatolik: {e}")
    finally:
        for f in os.listdir(TMP_DIR):
            try:
                os.remove(os.path.join(TMP_DIR, f))
            except:
                pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text or msg.caption or ""
    if not text.startswith("http"):
        await msg.reply_text("❌ To‘liq link yuboring.")
        return

    if not await is_subscribed(msg.from_user.id, context):
        await msg.reply_text(
            f"📢 Avval {CHANNEL_USERNAME} kanaliga obuna bo‘ling!",
            reply_markup=subscription_keyboard(),
        )
        return

    await process_and_send_media(msg, context, text.strip(), video_opts)

async def handle_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    args = context.args or []
    text = args[0] if args else msg.text.replace("/music", "").strip()

    if not text.startswith("http"):
        await msg.reply_text("🎵 Musiqa linkini yuboring.")
        return

    if not await is_subscribed(msg.from_user.id, context):
        await msg.reply_text(
            f"🎧 Avval {CHANNEL_USERNAME} kanaliga obuna bo‘ling!",
            reply_markup=subscription_keyboard(),
        )
        return

    await process_and_send_media(msg, context, text.strip(), audio_opts, True)

async def callback_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_subscribed(q.from_user.id, context):
        await q.edit_message_text("✅ Obuna tasdiqlandi! Endi link yuboring.")
    else:
        await q.edit_message_text(
            f"❌ Obuna topilmadi.
{CHANNEL_USERNAME} kanaliga obuna bo‘ling:",
            reply_markup=subscription_keyboard(),
        )

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("music", handle_music))
    app.add_handler(MessageHandler(filters.TEXT | filters.Caption(), handle_message))
    app.add_handler(CallbackQueryHandler(callback_check_subscription, pattern="^check_subscription$"))

    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
