from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

BOT_TOKEN = '8035303307:AAGWTKOaTMrwQrpKh1S2HRYZCcMoFFUIx0c'

# 🌐 Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ Railway’ga joylangan .env dan credentials o‘qish
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 📄 Google Sheets ID va varaq
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo/edit#gid=1450330100").sheet1

user_data = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {}

    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Xush kelibsiz!\n\n📞 Iltimos, telefon raqamingizni yuboring:", reply_markup=markup)

# Kontaktni qabul qilish
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user_data[user_id]['phone'] = contact.phone_number
    user_data[user_id]['name'] = f"{contact.first_name or ''} {contact.last_name or ''}".strip()

    await update.message.reply_text("🏙 Siz joylashgan hududni yozing:")

# Matnli javoblar (hudud, o‘lcham, manzil)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if 'region' not in user_data[user_id]:
        user_data[user_id]['region'] = text
        await update.message.reply_text("📸 Olishmoqchi bo‘lgan tovar rasmini yuboring:")
    elif 'photo' not in user_data[user_id]:
        await update.message.reply_text("📸 Iltimos, rasmni rasm sifatida yuboring.")
    elif 'size' not in user_data[user_id]:
        user_data[user_id]['size'] = text
        await update.message.reply_text("📍 Manzilingizni yozing:")
    elif 'address' not in user_data[user_id]:
        user_data[user_id]['address'] = text
        await save_data(update, context)

# Rasmni qabul qilish
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if 'region' not in user_data.get(user_id, {}):
        await update.message.reply_text("🏙 Avval hududni yozing.")
        return

    photo_file_id = update.message.photo[-1].file_id
    user_data[user_id]['photo'] = photo_file_id

    await update.message.reply_text("📏 O‘lchamingizni yozing:")

# Sheetsga yozish
async def save_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data[user_id]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    sheet.append_row([
        now,
        data.get('name', ''),
        data.get('phone', ''),
        data.get('region', ''),
        f"https://t.me/c/{update.message.chat_id}/{update.message.message_id - 2}",
        data.get('size', ''),
        data.get('address', '')
    ])

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!\n\n🔁 Yangi buyurtma uchun /start ni bosing.")
    user_data.pop(user_id, None)

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🚀 Bot ishga tushdi...")
    app.run_polling()
