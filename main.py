import os
import json
import pytz
import asyncio
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

(
    MAIN_MENU, ASK_LANG, ASK_PHONE, ENTER_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE,
    SETTINGS_MENU, CHANGE_LANG, CHANGE_REGION, CHANGE_NAME, CHANGE_PHONE, CHECK_SUB
) = range(13)

CHANNEL_LINK = "https://t.me/standartuzbekistan"
CHANNEL_USERNAME = "standartuzbekistan"

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
        'subscribe_text': "Botdan foydalanish uchun avval bizning rasmiy sahifamizga obuna bo‘ling:\n\n👉 [Standart Uzbekistan]({})\n\nObuna bo‘lgan bo‘lsangiz, '✅ Obuna bo‘ldim' tugmasini bosing!".format(CHANNEL_LINK),
        'sub_button': "✅ Obuna bo‘ldim",
        'not_subscribed': "❗ Obuna bo‘lmagansiz. Iltimos, [Standart Uzbekistan]({}) kanaliga obuna bo‘ling!".format(CHANNEL_LINK),
    },
    # ... RU blokini ham xohlasang qo‘shaman, qisqartirdim
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

# === 1. SUBSCRIBE CHECK ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    # Avval kanalga obuna bo‘lishni so‘raymiz
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(TEXTS['uz']['sub_button'], callback_data="check_sub")]]
    )
    await update.message.reply_text(
        TEXTS['uz']['subscribe_text'],
        reply_markup=kb,
        parse_mode="Markdown"
    )
    return CHECK_SUB

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Obuna bo‘lganini tekshiramiz
    bot = context.bot
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            raise Exception("Not subscribed")
    except:
        # Obuna bo‘lmasa, yana shu xabar chiqadi
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton(TEXTS['uz']['sub_button'], callback_data="check_sub")]]
        )
        await query.edit_message_text(
            TEXTS['uz']['not_subscribed'],
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return CHECK_SUB

    # === 2. Intro video chiqariladi ===
    try:
        with open("intro.mp4", "rb") as video:
            await bot.send_video_note(
                chat_id=query.message.chat.id,
                video_note=video
            )
        await asyncio.sleep(1)
    except Exception as e:
        await bot.send_message(chat_id=query.message.chat.id, text=f"❗ Video yuborishda xato: {e}")

    # Til tanlash menyusi
    markup = ReplyKeyboardMarkup(
        [[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await bot.send_message(
        chat_id=query.message.chat.id,
        text=TEXTS['uz']['choose_lang'],
        reply_markup=markup
    )
    return ASK_LANG

# ==== QOLGAN QISMLAR O‘ZGARMAYDI (AVVALGIDAN COPY) ====
# Yagona farq — entry_points: /start CallbackQueryHandler(check_sub) bilan

# ... (qolgan funksiya va ConversationHandler kodi SENING OXIRGI KODINGDAGIDAN KO‘CHIRILADI)

# YANGI ConversationHandler:
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
        states={
            CHECK_SUB: [CallbackQueryHandler(check_sub)],
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_phone)],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region)],
            ASK_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(filters.ALL, handle_photo)
            ],
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
