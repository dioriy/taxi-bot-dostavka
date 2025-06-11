import os
import json
import pytz
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

(
    MAIN_MENU, ASK_LANG, ASK_PHONE, ENTER_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE,
    SETTINGS_MENU, CHANGE_LANG, CHANGE_REGION, CHANGE_NAME, CHANGE_PHONE
) = range(12)

user_data = {}

def get_gs_client():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.loads(creds_json)
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(credentials)
    return client

def write_to_sheets(data):
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    SHEET_NAME = os.getenv("SHEET_NAME")
    gc = get_gs_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.append_row([
        data.get('name', ''),
        data.get('phone', ''),
        data.get('region', ''),
        data.get('size', ''),
        data.get('date', ''),
    ])

TEXTS = {
    'uz': {
        'menu': "👇 Menyu:",
        'profile': "👤 Profil",
        'settings': "⚙️ Sozlamalar",
        'order': "🛒 Yangi buyurtma",
        'choose_lang': "Iltimos, tilni tanlang:",
        'lang_uz': "🇺🇿 O'zbekcha",
        'lang_ru': "🇷🇺 Русский",
        'ask_phone': "Telefon raqamingizni ulashish yoki \"✍️ Qo‘lda kiritish\" tugmasini bosing:",
        'enter_phone': "📱 Telefon raqamingizni +998XXXXXXXXX shaklida kiriting:",
        'invalid_phone': "❌ <b>Xato!</b> Iltimos, quyidagi namunadek raqam kiriting:\n<b>+998889000232</b>",
        'phone_ok': "✅ Raqam qabul qilindi!",
        'ask_region': "📍 Viloyatingizni tanlang:",
        'ask_photo': "📸 Buyurtma uchun rasm yuboring:",
        'ask_size': "📏 O‘lchamingizni kiriting:",
        'order_success': "✅ Buyurtmangiz qabul qilindi!\n\nAsosiy menyuga qaytish uchun /menu ni bosing yoki 'Menyu' tugmasidan foydalaning.",
        'new_order': "🆕 Yangi buyurtma!\n👤 Ism: {name}\n📞 Tel: {phone}\n📍 Viloyat: {region}\n📏 O‘lcham: {size}\n🕰 Sana: {date}",
        'settings_menu': "⚙️ Sozlamalar menyusi:\n\nQuyidagilardan birini tanlang:",
        'change_lang': "🌐 Tilni o‘zgartirish",
        'change_region': "📍 Viloyatni o‘zgartirish",
        'change_name': "✏️ Ismni o‘zgartirish",
        'change_phone': "📞 Telefon raqamni o‘zgartirish",
        'back': "⬅️ Ortga",
        'profile_info': "👤 Sizning profilingiz:\n\nIsm: {name}\nTel: {phone}\nViloyat: {region}\nTil: {lang}",
        'set_name': "Yangi ismingizni kiriting:",
        'set_region': "Yangi viloyatingizni tanlang:",
        'set_phone': "Yangi telefon raqamingizni +998XXXXXXXXX ko‘rinishida kiriting:",
        'set_lang': "Yangi tilni tanlang:",
        'lang_name': {'uz': "O‘zbekcha", 'ru': "Ruscha"},
        'changed': "✅ O‘zgartirildi!",
        'menu_btns': [["🛒 Yangi buyurtma"], ["👤 Profil", "⚙️ Sozlamalar"]],
    },
    'ru': {
        'menu': "👇 Меню:",
        'profile': "👤 Профиль",
        'settings': "⚙️ Настройки",
        'order': "🛒 Новый заказ",
        'choose_lang': "Пожалуйста, выберите язык:",
        'lang_uz': "🇺🇿 Узбекский",
        'lang_ru': "🇷🇺 Русский",
        'ask_phone': "Отправьте свой номер или нажмите кнопку \"✍️ Ввести вручную\":",
        'enter_phone': "📱 Введите ваш номер в формате +998XXXXXXXXX:",
        'invalid_phone': "❌ <b>Ошибка!</b> Введите номер в формате:\n<b>+998889000232</b>",
        'phone_ok': "✅ Номер принят!",
        'ask_region': "📍 Выберите свой регион:",
        'ask_photo': "📸 Отправьте фото товара для заказа:",
        'ask_size': "📏 Введите ваш размер:",
        'order_success': "✅ Ваш заказ принят!\n\nДля возврата в главное меню нажмите /menu или используйте кнопку 'Меню'.",
        'new_order': "🆕 Новый заказ!\n👤 Имя: {name}\n📞 Тел: {phone}\n📍 Регион: {region}\n📏 Размер: {size}\n🕰 Дата: {date}",
        'settings_menu': "⚙️ Меню настроек:\n\nВыберите один из пунктов:",
        'change_lang': "🌐 Изменить язык",
        'change_region': "📍 Изменить регион",
        'change_name': "✏️ Изменить имя",
        'change_phone': "📞 Изменить телефон",
        'back': "⬅️ Назад",
        'profile_info': "👤 Ваш профиль:\n\nИмя: {name}\nТел: {phone}\nРегион: {region}\nЯзык: {lang}",
        'set_name': "Введите новое имя:",
        'set_region': "Выберите новый регион:",
        'set_phone': "Введите новый номер в формате +998XXXXXXXXX:",
        'set_lang': "Выберите новый язык:",
        'lang_name': {'uz': "Узбекский", 'ru': "Русский"},
        'changed': "✅ Изменено!",
        'menu_btns': [["🛒 Новый заказ"], ["👤 Профиль", "⚙️ Настройки"]],
    }
}

REGIONS = [
    ["Toshkent", "Andijon", "Farg‘ona"],
    ["Namangan", "Buxoro", "Jizzax"],
    ["Xorazm", "Qashqadaryo", "Samarqand"],
    ["Surxondaryo", "Sirdaryo", "Navoiy"],
    ["Qoraqalpog‘iston"]
]

def get_lang(user_id):
    return user_data.get(user_id, {}).get("lang", "uz")

def t(user_id, key):
    lang = get_lang(user_id)
    return TEXTS[lang][key]

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    markup = ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    await update.message.reply_text(t(user_id, 'menu'), reply_markup=markup)
    return MAIN_MENU

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    # 🎥 Video yuboriladi
    try:
        with open("intro.mp4", "rb") as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption="Assalomu alaykum! Bu bizning xizmatimiz haqida qisqacha video 🎥"
            )
    except Exception as e:
        await update.message.reply_text(f"❗ Video yuborishda xato: {e}")

    # 🌐 Til tanlash menyusi
    markup = ReplyKeyboardMarkup(
        [[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(TEXTS['uz']['choose_lang'], reply_markup=markup)
    return ASK_LANG

# ❗ Quyida qolgan koding o‘zgarishsiz qoladi (telefon, viloyat, buyurtma, profil va boshqalar)
# SENDAN AVVAL YUBORILGAN VERSIYA TO‘LIQ ISHLAYDI, FAQAT `start()` FUNKSIYASI YANGILANDI

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
        states={
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_phone)],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region)],
            ASK_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            ASK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_size)],
            SETTINGS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_menu_handler)],
            CHANGE_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_lang)],
            CHANGE_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_region)],
            CHANGE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_name)],
            CHANGE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_phone)],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
    )
    app.add_handler(conv_handler)
    print("✅ Bot ishga tushdi, buyurtmalar va profil uchun tayyor!")
    app.run_polling()
