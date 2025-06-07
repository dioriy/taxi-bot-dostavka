import os
import io
import json
import gspread
import requests
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# ⏬ .env faylni yuklaymiz
load_dotenv()

# ⏬ .env dan ma'lumotlar
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# ⏬ JSON matnni dict holatga keltiramiz
creds_dict = json.loads(GOOGLE_CREDS_JSON)

# Google API ulanish
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo").sheet1
drive_service = build("drive", "v3", credentials=credentials)

# 🔄 Vaqtinchalik foydalanuvchi ma'lumotlari
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {"step": "phone"}
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Xush kelibsiz!\n\n📞 Telefon raqamingizni yuboring:", reply_markup=markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user_data[user_id]['phone'] = contact.phone_number
    user_data[user_id]['name'] = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    user_data[user_id]['step'] = "region"
    await update.message.reply_text("🌍 Siz joylashgan hududni yozing:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    step = user_data.get(user_id, {}).get("step")

    if step == "region":
        user_data[user_id]["region"] = text
        user_data[user_id]["step"] = "size"
        await update.message.reply_text("📸 Olishmoqchi bo‘lgan tovar rasmini yuboring:")
    elif step == "size":
        await update.message.reply_text("📸 Iltimos, rasmni rasm sifatida yuboring.")
    elif step == "address":
        user_data[user_id]["address"] = text
        await save_to_sheet(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    step = user_data.get(user_id, {}).get("step")

    if step != "size":
        return await update.message.reply_text("📍 Avval hududni kiriting!")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()

    file_metadata = {
        "name": f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
        "parents": ["root"]
    }
    media = {
        "data": io.BytesIO(file_bytes),
        "mimeType": "image/jpeg"
    }
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media["data"],
        fields="id"
    ).execute()

    file_id = uploaded_file.get("id")
    drive_service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()
    image_link = f"https://drive.google.com/open?id={file_id}"

    user_data[user_id]["image_url"] = image_link
    user_data[user_id]["step"] = "address"
    await update.message.reply_text("📍 Yuboriladigan aniq manzilingizni yozing:")

async def save_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data[user_id]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    sheet.append_row([
        now,
        data.get("name", ""),
        data.get("phone", ""),
        data.get("region", ""),
        data.get("image_url", ""),
        "",  # Size bo‘sh, hozircha kiritilmayapti
        data.get("address", "")
    ])

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!\n\nYangi buyurtma uchun /start ni bosing.")
    user_data.pop(user_id, None)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
