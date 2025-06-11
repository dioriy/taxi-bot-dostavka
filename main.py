import os
import json
import pytz
import asyncio
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

(
    MAIN_MENU, ASK_LANG, ASK_PHONE, ENTER_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE,
    SETTINGS_MENU, CHANGE_LANG, CHANGE_REGION, CHANGE_NAME, CHANGE_PHONE, CHECK_SUB
) = range(13)

CHANNEL_USERNAME = "standartuzbekistan"  # obuna bo‘lishi shart bo‘lgan kanal

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
        'subscribe_text': "Botdan foydalanish uchun avval <a href='https://t.me/standartuzbekistan'>standartuzbekistan</a> kanaliga obuna bo‘ling!\n\nObuna bo‘lganingizdan so‘ng <b>✅ Tasdiqlash</b> tugmasini bosing.",
        'confirm': "✅ Tasdiqlash"
    },
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

# ---------- OBUNA BOSQICHI -------------
async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status in ['member', 'creator', 'administrator']:
            # Obuna bo‘lgan, keyingi bosqich
            return await start_step2(update, context)
        else:
            return await ask_sub(update, context)
    except Exception as e:
        return await ask_sub(update, context)

async def ask_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data="checksub")]
    ])
    await update.message.reply_text(
        TEXTS['uz']['subscribe_text'],
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    return CHECK_SUB

async def confirm_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
    if member.status in ['member', 'creator', 'administrator']:
        await query.edit_message_text("Obuna muvaffaqiyatli! Davom etamiz ⬇️")
        # Boshlanishga o'tish
        fake_update = Update.de_json(update.to_dict(), context.bot)
        fake_update.effective_user = query.from_user
        fake_update.effective_chat = query.message.chat
        return await start_step2(fake_update, context)
    else:
        await query.answer("Iltimos, avval kanalga obuna bo‘ling!", show_alert=True)
        return CHECK_SUB

# ---------- BOTNING BOSHI /start va asosiy intro video -------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await ask_sub(update, context)

async def start_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    # 🎥 Dumaloq video (intro)
    try:
        with open("intro.mp4", "rb") as video:
            await context.bot.send_video_note(
                chat_id=update.effective_chat.id,
                video_note=video
            )
    except Exception as e:
        await update.message.reply_text(f"❗ Video yuborishda xato: {e}")

    markup = ReplyKeyboardMarkup(
        [[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(TEXTS['uz']['choose_lang'], reply_markup=markup)
    return ASK_LANG

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    markup = ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    await update.message.reply_text(t(user_id, 'menu'), reply_markup=markup)
    return MAIN_MENU

# --- Qolgan funksiyalar (ask_lang, ask_phone, handle_phone...) sendagi oxirgi main.py'dan olib joylashtir ---
# Yoki avvalgi kodingdan to‘liq olib quyidagidek joylashtir.

# ... Boshqa funksiyalarni (ask_lang, main_menu_handler, ask_phone, ... va boshqalar) ham o‘z o‘rnida yozib chiq!

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
        states={
            CHECK_SUB: [CallbackQueryHandler(confirm_sub, pattern="checksub")],
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            # Qolgan bosqichlar...
            # ASK_PHONE, ENTER_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE, ...
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
    )
    app.add_handler(conv_handler)
    print("✅ Bot ishga tushdi, buyurtmalar va profil uchun tayyor!")
    app.run_polling()
