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

# === Sozlamalar ===
TELEGRAM_TOKEN = "8454214201:AAF2l1po3Etal89x-ZkcuBEn0Xy3GVhbC14"
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

# === Obuna tekshiruvi ===
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

# === /start komandasi ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Link yuboring (Instagram, YouTube, TikTok, Facebook...) — men uni video, rasm yoki audio qilib qaytaraman.\n"
        "🎵 Faqat musiqa yuklash uchun: /music <link>\n\n"
        f"📢 Eslatma: media olish uchun avval {CHANNEL_USERNAME} kanaliga obuna bo‘ling."
    )

# === Yuklab olish funksiyasi ===
def download_media(url, opts):
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if opts is audio_opts:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info

# === Media yuborish jarayoni ===
async def process_and_send_media(msg, context, url, opts, is_audio=False):
    status_msg = await msg.reply_text("⏳ Yuklanmoqda...")
    try:
        loop = asyncio.get_running_loop()
        filename, info = await loop.run_in_executor(None, lambda: download_media(url, opts))

        if not os.path.exists(filename):
            await status_msg.edit_text("⚠️ Fayl topilmadi yoki qo‘llab-quvvatlanmaydi.")
            return

        title = info.get("title", "Media")
        caption = f"📥 Yuklandi: {title}"

        ext = os.path.splitext(filename)[1].lower()
        if is_audio or ext in [".mp3", ".m4a", ".aac", ".ogg"]:
            with open(filename, "rb") as f:
                await msg.reply_audio(audio=InputFile(f, filename=os.path.basename(filename)), caption=caption)
        elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
            with open(filename, "rb") as f:
                await msg.reply_video(video=InputFile(f), caption=caption)
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            with open(filename, "rb") as f:
                await msg.reply_photo(photo=InputFile(f), caption=caption)
        else:
            with open(filename, "rb") as f:
                await msg.reply_document(document=InputFile(f), caption=caption)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Xatolik yuz berdi: {e}")
    finally:
        try:
            for f in os.listdir(TMP_DIR):
                os.remove(os.path.join(TMP_DIR, f))
        except:
            pass

# === Link yuborilganda ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text or msg.caption or ""
    if not text or not text.startswith("http"):
        await msg.reply_text("❌ Iltimos, to‘liq link yuboring.")
        return

    user_id = msg.from_user.id
    subscribed = await is_subscribed(user_id, context)

    if not subscribed:
        await msg.reply_text(
            f"📢 Media olishdan oldin {CHANNEL_USERNAME} kanaliga obuna bo‘ling!",
            reply_markup=subscription_keyboard(),
        )
        return

    await process_and_send_media(msg, context, text.strip(), video_opts)

# === /music komandasi ===
async def handle_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    args = context.args or []
    if args:
        text = args[0]
    else:
        text = msg.text.replace("/music", "").strip()

    if not text or not text.startswith("http"):
        await msg.reply_text("🎵 Iltimos, musiqa link yuboring (YouTube, TikTok...).")
        return

    user_id = msg.from_user.id
    subscribed = await is_subscribed(user_id, context)

    if not subscribed:
        await msg.reply_text(
            f"🎧 Musiqa olishdan oldin {CHANNEL_USERNAME} kanaliga obuna bo‘ling!",
            reply_markup=subscription_keyboard(),
        )
        return

    await process_and_send_media(msg, context, text.strip(), audio_opts, is_audio=True)

# === "Tekshirish" tugmasi bosilganda ===
async def callback_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    subscribed = await is_subscribed(user_id, context)

    if subscribed:
        await q.edit_message_text("✅ Siz kanalga obuna bo‘lgansiz! Endi link yuboring.")
    else:
        await q.edit_message_text(
            f"❌ Hali obuna emassiz.\nIltimos {CHANNEL_USERNAME} kanaliga obuna bo‘ling:",
            reply_markup=subscription_keyboard(),
        )

# === Botni ishga tushirish ===
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
