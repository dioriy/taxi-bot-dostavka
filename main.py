import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv

# .env fayldan ma'lumotlarni olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
creds_json = os.getenv("GOOGLE_CREDS_JSON")

# Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import json
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo/edit#gid=1450330100").sheet1

# Guruh chat ID
GROUP_CHAT_ID = -4786339709

# Userlar ma’lumotlarini vaqtincha saqlovchi dict
user_data = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    button = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📞 Telefon raqamingizni yuboring:", reply_markup=markup)

# Kontaktni qabul qilish
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user_data[user_id]['phone'] = contact.phone_number
    user_data[user_id]['name'] = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    await update.message.reply_text("📍 Qaysi hududdasiz?")

# Matnlar bilan ishlash
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if 'region' not in user_data[user_id]:
        user_data[user_id]['region'] = text
        await update.message.reply_text("📸 Tovarning rasmini yuboring:")
    elif 'photo' not in user_data[user_id]:
        await update.message.reply_text("❗ Iltimos, rasmni rasm sifatida yuboring.")
    elif 'size' not in user_data[user_id]:
        user_data[user_id]['size'] = text
        await update.message.reply_text("📦 Manzilingizni kiriting:")
    elif 'address' not in user_data[user_id]:
        user_data[user_id]['address'] = text
        await save_and_send(update, context)

# Rasmni qabul qilish
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if 'region' not in user_data.get(user_id, {}):
        await update.message.reply_text("❗ Avval hududni yozing.")
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id
    user_data[user_id]['photo'] = file_id

    await update.message.reply_text("📏 O‘lchamingizni yozing:")

# Ma’lumotlarni Google Sheets va guruhga yuborish
async def save_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data[user_id]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Google Sheets'ga yozish
    sheet.append_row([
        now,
        data.get('name', ''),
        data.get('phone', ''),
        data.get('region', ''),
        'Telegram orqali yuborilgan',
        data.get('size', ''),
        data.get('address', '')
    ])

    # Guruhga xabar yuborish + rasm bilan
    caption = (
        f"📦 *Yangi buyurtma:*\n"
        f"👤 {data.get('name')}\n"
        f"📞 {data.get('phone')}\n"
        f"🏙 Hudud: {data.get('region')}\n"
        f"📏 O‘lcham: {data.get('size')}\n"
        f"📍 Manzil: {data.get('address')}\n"
        f"🕒 {now}"
    )
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=data.get('photo'), caption=caption, parse_mode="Markdown")

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!\n\nYangi buyurtma uchun /start ni bosing.")
    user_data.pop(user_id, None)

# Botni ishga tushurish
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
