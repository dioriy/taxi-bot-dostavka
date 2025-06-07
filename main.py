import os
import json
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

# Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo/edit#gid=1450330100").sheet1

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data.setdefault(user_id, {})
    
    if 'phone' not in user_data[user_id]:
        contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("📞 Telefon raqamingizni yuboring:", reply_markup=markup)
    elif 'region' not in user_data[user_id]:
        await ask_region(update)
    else:
        await update.message.reply_text("📸 Tovar rasmini yuboring:")

async def ask_region(update):
    regions = ["Toshkent", "Andijon", "Namangan", "Farg‘ona", "Buxoro", "Jizzax",
               "Xorazm", "Qashqadaryo", "Surxondaryo", "Samarqand", "Navoiy", "Sirdaryo"]
    buttons = [[KeyboardButton(region)] for region in regions]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📍 Qaysi viloyatdasiz?", reply_markup=markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user_data[user_id] = {
        'phone': contact.phone_number,
        'name': f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    }
    await ask_region(update)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    data = user_data.get(user_id, {})

    if 'phone' in data and 'region' not in data:
        user_data[user_id]['region'] = text
        await update.message.reply_text("📸 Tovar rasmini yuboring:")
    elif 'photo' in data and 'size' not in data:
        user_data[user_id]['size'] = text
        await save_and_send(update, context)
    elif 'photo' not in data:
        await update.message.reply_text("📸 Iltimos, avval rasm yuboring.")
    else:
        await update.message.reply_text("📏 Iltimos, o‘lchamingizni kiriting:")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if 'region' not in user_data.get(user_id, {}):
        await ask_region(update)
        return

    photo = update.message.photo[-1].file_id
    user_data[user_id]['photo'] = photo
    await update.message.reply_text("📏 O‘lchamingizni kiriting:")

async def save_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data[user_id]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Google Sheets'ga yozish
    sheet.append_row([
        now,
        data.get("name", ""),
        data.get("phone", ""),
        data.get("region", ""),
        "Telegram orqali rasm",
        data.get("size", "")
    ])

    # Telegram guruhga yuborish
    msg = (
        f"📦 *Yangi zakaz:*\n\n"
        f"👤 {data.get('name')}\n"
        f"📞 {data.get('phone')}\n"
        f"📍 {data.get('region')}\n"
        f"📏 O‘lcham: {data.get('size')}\n"
        f"🕒 Sana: {now}"
    )
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=data['photo'], caption=msg, parse_mode="Markdown")

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!\n\n🆕 Yangi buyurtma uchun /start ni bosing.")
    user_data.pop(user_id, None)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Bot ishga tushdi...")
    app.run_polling()
