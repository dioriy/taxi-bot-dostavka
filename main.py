import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = -4786339709  # Guruh ID

# States
ASK_LANG, ASK_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE = range(5)

user_data = {}

# --- Til bo‘yicha lug‘atlar ---
TEXTS = {
    'uz': {
        'choose_lang': "Iltimos, tilni tanlang:",
        'lang_uz': "🇺🇿 O'zbekcha",
        'lang_ru': "🇷🇺 Русский",
        'ask_phone': "📞 Telefon raqamingizni ulashing yoki +998XXXXXXXXX tarzda qo‘lda kiriting:",
        'invalid_phone': "❌ Telefon raqam formati xato. Namuna: +998889000232",
        'ask_region': "📍 Viloyatingizni tanlang:",
        'ask_photo': "📸 Buyurtma uchun rasm yuboring:",
        'ask_size': "📏 O‘lchamingizni kiriting:",
        'order_success': "✅ Buyurtmangiz qabul qilindi! Yangi buyurtma uchun /start ni bosing.",
        'new_order': "🆕 Yangi buyurtma!\n👤 Ism: {name}\n📞 Tel: {phone}\n📍 Viloyat: {region}\n📏 O‘lcham: {size}\n🕰 Sana: {date}",
    },
    'ru': {
        'choose_lang': "Пожалуйста, выберите язык:",
        'lang_uz': "🇺🇿 O'zbekский",
        'lang_ru': "🇷🇺 Русский",
        'ask_phone': "📞 Отправьте свой номер или введите в формате +998XXXXXXXXX:",
        'invalid_phone': "❌ Неправильный формат номера. Пример: +998889000232",
        'ask_region': "📍 Выберите свой регион:",
        'ask_photo': "📸 Отправьте фото товара для заказа:",
        'ask_size': "📏 Введите ваш размер:",
        'order_success': "✅ Ваш заказ принят! Для нового заказа нажмите /start.",
        'new_order': "🆕 Новый заказ!\n👤 Имя: {name}\n📞 Тел: {phone}\n📍 Регион: {region}\n📏 Размер: {size}\n🕰 Дата: {date}",
    }
}

REGIONS = [
    ["Toshkent", "Andijon", "Farg‘ona"],
    ["Namangan", "Buxoro", "Jizzax"],
    ["Xorazm", "Qashqadaryo", "Samarqand"],
    ["Surxondaryo", "Sirdaryo", "Navoiy"],
    ["Qoraqalpog‘iston"]
]

def get_text(user_id, key):
    lang = user_data.get(user_id, {}).get("lang", "uz")
    return TEXTS[lang][key]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Tilni tanlash klaviaturasi
    lang_btns = [[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]]
    markup = ReplyKeyboardMarkup(lang_btns, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(TEXTS['uz']['choose_lang'], reply_markup=markup)
    return ASK_LANG

async def ask_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    # Qaysi til tanlandi
    if 'O‘zbek' in text or 'O\'zbek' in text:
        lang = 'uz'
    elif 'Русский' in text or 'Русский' in text:
        lang = 'ru'
    else:
        lang = 'uz'
    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['lang'] = lang

    # Telefon raqam so‘raymiz
    contact_btn = KeyboardButton(get_text(user_id, 'ask_phone'), request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn], ["✍️ Qo‘lda kiritish"]], resize_keyboard=True)
    await update.message.reply_text(get_text(user_id, 'ask_phone'), reply_markup=markup)
    return ASK_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact

    if contact:
        phone = contact.phone_number
        name = contact.first_name or ""
    else:
        phone = update.message.text.strip()
        name = update.effective_user.first_name or ""
        if not phone.startswith("+998") or len(phone) != 13:
            await update.message.reply_text(get_text(user_id, 'invalid_phone'))
            return ASK_PHONE

    user_data[user_id]["phone"] = phone
    user_data[user_id]["name"] = name

    markup = ReplyKeyboardMarkup(REGIONS, resize_keyboard=True)
    await update.message.reply_text(get_text(user_id, 'ask_region'), reply_markup=markup)
    return ASK_REGION

async def handle_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    region = update.message.text.strip()
    user_data[user_id]["region"] = region
    await update.message.reply_text(get_text(user_id, 'ask_photo'))
    return ASK_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file_id = update.message.photo[-1].file_id
    user_data[user_id]["photo"] = photo_file_id
    await update.message.reply_text(get_text(user_id, 'ask_size'))
    return ASK_SIZE

async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    size = update.message.text.strip()
    user_data[user_id]["size"] = size

    data = user_data[user_id]
    text = get_text(user_id, 'new_order').format(
        name=data.get('name', 'Noma’lum'),
        phone=data.get('phone', 'Noma’lum'),
        region=data.get('region', 'Noma’lum'),
        size=data.get('size', ''),
        date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    await context.bot.send_photo(
        chat_id=GROUP_CHAT_ID,
        photo=data["photo"],
        caption=text
    )
    await update.message.reply_text(get_text(user_id, 'order_success'))
    return ConversationHandler.END

async def manual_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_phone(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_phone)
            ],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region)],
            ASK_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            ASK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_size)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    print("✅ Bot ishga tushdi, buyurtmalar uchun tayyor!")
    app.run_polling()
