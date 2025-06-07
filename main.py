import os
import io
import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Google API sozlamalari
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(creds_json), scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo/edit#gid=1450330100").sheet1
drive_service = build("drive", "v3", credentials=creds)

BOT_TOKEN = os.getenv("BOT_TOKEN")
user_data = {}

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    button = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Xush kelibsiz!\n📞 Telefon raqamingizni yuboring:", reply_markup=markup)

# Telefon raqami
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    user_data[user_id]["phone"] = contact.phone_number
    user_data[user_id]["name"] = contact.first_name
    await update.message.reply_text("🏙 Joylashgan hududingizni yozing:")

# Matnli javoblar
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if "region" not in user_data[user_id]:
        user_data[user_id]["region"] = text
        await update.message.reply_text("📸 Tovar rasmini yuboring:")
    elif "size" not in user_data[user_id]:
        user_data[user_id]["size"] = text
        await update.message.reply_text("📍 Manzilingizni yozing:")
    elif "address" not in user_data[user_id]:
        user_data[user_id]["address"] = text
        await save_data(update)

# Rasm
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    bio = io.BytesIO()
    await file.download(out=bio)
    bio.seek(0)

    filename = f"zakaz_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    media = MediaIoBaseUpload(bio, mimetype="image/jpeg")
    file_metadata = {"name": filename}

    loop = asyncio.get_event_loop()
    try:
        file_drive = await loop.run_in_executor(
            None,
            lambda: drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
        )

        # Ruxsat berish
        await loop.run_in_executor(
            None,
            lambda: drive_service.permissions().create(
                fileId=file_drive["id"],
                body={"type": "anyone", "role": "reader"}
            ).execute()
        )

        image_url = f"https://drive.google.com/open?id={file_drive['id']}"
        user_data[user_id]["photo"] = image_url
        await update.message.reply_text("📏 O‘lchamingizni yozing:")
    except Exception as e:
        logging.error(f"Google Drive xatosi: {e}")
        await update.message.reply_text("❌ Rasmni yuklashda xatolik. Qaytadan urinib ko‘ring.")

# Ma'lumotni Sheetsga yozish
async def save_data(update: Update):
    user_id = update.effective_user.id
    data = user_data[user_id]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([
        now,
        data.get("name", ""),
        data.get("phone", ""),
        data.get("region", ""),
        data.get("photo", ""),
        data.get("size", ""),
        data.get("address", "")
    ])

    await update.message.reply_text("✅ Buyurtma qabul qilindi!\nYangi buyurtma uchun /start buyrug‘ini bosing.")
    user_data.pop(user_id, None)

# App
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Bot ishga tushdi.")
    app.run_polling()
