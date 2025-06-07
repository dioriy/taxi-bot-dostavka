import os
import json
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROUP_CHAT_ID = -4786339709  # O'zgartirish kerak bo‘lsa, .envdan olasan
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")

# Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1iZqsydjfN7hW6xKMsctHcc1gUrMR8o5cbACd3_Arfyo/edit#gid=1450330100"
).sheet1

user_states = {}  # Foydalanuvchi bosqichlarini saqlash uchun
user_data = {}    # Foydalanuvchi ma’lumotlarini saqlash uchun

# Viloyatlar ro'yxati
regions = [
    "Toshkent", "Toshkent viloyati", "Andijon", "Farg‘ona", "Namangan",
    "Samarqand", "Buxoro", "Jizzax", "Sirdaryo", "Surxondaryo",
    "Qashqadaryo", "Navoiy", "Xorazm", "Qoraqalpog‘iston"
]

def get_region_keyboard():
    rows = []
    for i in range(0, len(regions), 2):
        rows.append([regions[i], regions[i+1]] if i+1 < len(regions) else [regions[i]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
        user_states[user_id] = 'ask_contact'
        contact_btn = KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "👋 Xush kelibsiz!\n\n📞 Iltimos telefon raqamingizni ulashishingizni so‘raymiz:", reply_markup=markup)
    else:
        # Agar allaqachon kontakt berilgan bo'lsa
        user_states[user_id] = 'ask_region'
        await update.message.reply_text(
            "📍 Qaysi viloyatdasiz?", reply_markup=get_region_keyboard()
        )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    user_data[user_id] = {
        "name": f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
        "phone": contact.phone_number,
    }
    user_states[user_id] = 'ask_region'
    await update.message.reply_text(
        "📍 Buyurtmani qayerga yuboraylik?", reply_markup=get_region_keyboard()
    )

async def handle_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if text not in regions:
        await update.message.reply_text("Iltimos, quyidagi viloyatlardan birini tanlang.", reply_markup=get_region_keyboard())
        return
    user_data[user_id]['region'] = text
    user_states[user_id] = 'ask_photo'
    await update.message.reply_text("🖼 Iltimos sizga yoqgan maxsulotimiz rasmini yuboring:", reply_markup=ReplyKeyboardRemove())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Rasmni olamiz va file_id ni saqlaymiz
    photo = update.message.photo[-1]
    file_id = photo.file_id
    user_data[user_id]['photo_file_id'] = file_id
    user_states[user_id] = 'ask_size'
    await update.message.reply_text("📏 Iltimos o‘lchamingizni kiriting:")

async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    size = update.message.text
    user_data[user_id]['size'] = size

    # Ma’lumotlarni Google Sheetsga yozamiz
    data = user_data[user_id]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Rasm havolasini Telegram uchun tayyorlaymiz
    photo_link = f"https://t.me/{context.bot.username}?start={data['photo_file_id']}"

    sheet.append_row([
        now,
        data.get('name', ''),
        data.get('phone', ''),
        data.get('region', ''),
        photo_link,   # Rasmni ko‘rish uchun havola (file_id saqlanadi)
        data.get('size', ''),
    ])

    # Telegram guruhga xabar yuboramiz (rasm bilan)
    caption = (
        f"🆕 Yangi buyurtma!\n"
        f"👤 Ism: {data.get('name', '')}\n"
        f"📞 Tel: {data.get('phone', '')}\n"
        f"📍 Viloyat: {data.get('region', '')}\n"
        f"📏 O‘lcham: {data.get('size', '')}\n"
        f"🕑 Sana: {now}"
    )
    await context.bot.send_photo(
        chat_id=GROUP_CHAT_ID,
        photo=data['photo_file_id'],
        caption=caption
    )

    await update.message.reply_text(
        "✅ Buyurtmangiz qabul qilindi! tez orada bizning operatorlarimiz siz bilan bog'lanishadi \n\nYana buyurtma uchun /start ni bosing."
    )

    # Foydalanuvchi holatini tozalash – ammo kontakt va ismni eslab qolamiz
    user_states[user_id] = 'ask_region'  # Keyingi safar regiondan boshlanadi

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, None)
    if state == 'ask_region':
        await handle_region(update, context)
    elif state == 'ask_size':
        await handle_size(update, context)
    else:
        await update.message.reply_text("Iltimos, botdan to‘g‘ri foydalaning yoki /start buyrug‘ini bosing.")

async def handle_photo_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, None)
    if state == 'ask_photo':
        await handle_photo(update, context)
    else:
        await update.message.reply_text("Hozir rasm yuborishingiz shart emas. /start ni bosing.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_wrapper))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__':
    main()
