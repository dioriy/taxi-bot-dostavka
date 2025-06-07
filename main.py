import os
import io
import json
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv

# Logger
logging.basicConfig(level=logging.INFO)

# .env faylni yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

# Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo").sheet1

# Google Drive ulanish
drive_service = build("drive", "v3", credentials=credentials)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Xush kelibsiz!\n\n📞 Iltimos, telefon raqamingizni yuboring:", reply_markup=markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    user_data[user_id]["name"] = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    user_data[user_id]["phone"] = contact.phone_number
    await update.message.reply_text("🌍 Siz joylashgan hududni yozing:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Iltimos, /start buyrug‘i bilan boshlang.")
        return

    data = user_data[user_id]
    if "region" not in data:
        data["region"] = text
        await update.message.reply_text("📸 Olishmoqchi bo‘lgan tovar rasmini yuboring (Skrenshot):")
    elif "size" not in data:
        data["size"] = text
        await update.message.reply_text("📍 Yuboriladigan manzilni yozing:")
    elif "address" not in data:
        data["address"] = text
        await save_to_sheet(update, context, user_id)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or "region" not in user_data[user_id]:
        await update.message.reply_text("Iltimos, hududni avval yozing.")
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await file.download(out=bio)
    bio.seek(0)

    # Google Drive'ga yuklash
    filename = f"zakaz_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    media = MediaIoBaseUpload(bio, mimetype='image/jpeg')
    file_metadata = {
        'name': filename,
        'parents': []  # agar maxsus papka bo‘lsa, shu yerga parent ID qo‘shasiz
    }
    file_drive = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Ko‘rish mumkin bo‘lgan havola qilish
    drive_service.permissions().create(
        fileId=file_drive['id'],
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()
    image_url = f"https://drive.google.com/open?id={file_drive['id']}"
    user_data[user_id]['photo_url'] = image_url

    await update.message.reply_text("📏 O‘lchamingizni yozing:")

async def save_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    data = user_data[user_id]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sheet.append_row([
        timestamp,
        data.get('name', ''),
        data.get('phone', ''),
        data.get('region', ''),
        data.get('photo_url', ''),
        data.get('size', ''),
        data.get('address', '')
    ])

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!\n/start buyrug‘i orqali yangi buyurtma berishingiz mumkin.")
    user_data.pop(user_id)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Bot ishga tushdi...")
    app.run_polling()
