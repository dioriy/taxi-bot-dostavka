import os
import json
import pytz
import asyncio
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

(
    MAIN_MENU, ASK_LANG, ASK_PHONE, ENTER_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE,
    SETTINGS_MENU, CHANGE_LANG, CHANGE_REGION, CHANGE_NAME, CHANGE_PHONE, CHECK_SUB
) = range(13)

user_data = {}

CHANNEL_USERNAME = "standartuzbekistan"  # faqat username, @siz

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
        'subscribe': "Botdan foydalanish uchun 👉 [STANDART UZBEKISTAN](https://t.me/standartuzbekistan) kanaliga obuna bo‘ling.\n\nObuna bo‘lganingizdan so‘ng '✅ Tasdiqlash' tugmasini bosing.",
        'confirm': "✅ Tasdiqlash",
        'not_subscribed': "Iltimos, avval kanalga obuna bo‘ling!",
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
        'subscribe': "Для использования бота подпишитесь на 👉 [STANDART UZBEKISTAN](https://t.me/standartuzbekistan).\n\nПосле подписки нажмите кнопку '✅ Подтвердить'.",
        'confirm': "✅ Подтвердить",
        'not_subscribed': "Пожалуйста, сначала подпишитесь на канал!",
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

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obuna tekshiruvi"""
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
    return member.status in ("member", "administrator", "creator")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    # OBUNA TEKSHIRUV
    subscribed = await check_subscription(update, context)
    if not subscribed:
        lang = user_data.get(user_id, {}).get("lang", "uz")
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(user_id, 'confirm'), callback_data="check_subscribe")]
        ])
        await update.message.reply_text(
            t(user_id, 'subscribe'),
            reply_markup=btn,
            parse_mode="Markdown"
        )
        return CHECK_SUB

    # 1. Intro video
    try:
        with open("intro.mp4", "rb") as video:
            await context.bot.send_video_note(chat_id=update.effective_chat.id, video_note=video)
    except Exception as e:
        await update.message.reply_text(f"❗ Intro video xato: {e}")

    # Til tanlash
    markup = ReplyKeyboardMarkup(
        [[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(TEXTS['uz']['choose_lang'], reply_markup=markup)
    return ASK_LANG

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    subscribed = await check_subscription(update, context)
    if subscribed:
        await query.message.delete()
        # Yangi start chaqirilsin
        fake_update = Update.de_json({'message': {
            'message_id': 1, 'from': {'id': user_id}, 'chat': {'id': user_id}, 'date': 0
        }}, context.bot)
        return await start(fake_update, context)
    else:
        await query.answer(t(user_id, 'not_subscribed'), show_alert=True)
        return CHECK_SUB

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    markup = ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    await update.message.reply_text(t(user_id, 'menu'), reply_markup=markup)
    return MAIN_MENU

async def ask_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if 'O‘zbek' in text or 'O\'zbek' in text or 'Uzbek' in text:
        lang = 'uz'
    elif 'Русский' in text or 'Russian' in text:
        lang = 'ru'
    else:
        lang = 'uz'
    user_data[user_id]['lang'] = lang
    await menu(update, context)
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if t(user_id, 'order') in text:
        if user_id in user_data and user_data[user_id].get("phone") and user_data[user_id].get("region"):
            # 2. Rasm uchun video note
            try:
                with open("photo_note.mp4", "rb") as vnote:
                    await context.bot.send_video_note(
                        chat_id=update.effective_chat.id,
                        video_note=vnote
                    )
                await asyncio.sleep(2)
            except Exception as e:
                await update.message.reply_text(f"❗ Video yuborishda xato: {e}")
            await update.message.reply_text(t(user_id, 'ask_photo'), reply_markup=ReplyKeyboardRemove())
            return ASK_PHOTO
        else:
            return await ask_phone(update, context)
    elif t(user_id, 'profile') in text:
        info = user_data[user_id]
        await update.message.reply_text(
            t(user_id, 'profile_info').format(
                name=info.get('name', '-'),
                phone=info.get('phone', '-'),
                region=info.get('region', '-'),
                lang=TEXTS[get_lang(user_id)]['lang_name'][get_lang(user_id)]
            ),
            reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
        )
        return MAIN_MENU
    elif t(user_id, 'settings') in text:
        btns = [
            [t(user_id, 'change_lang')],
            [t(user_id, 'change_region')],
            [t(user_id, 'change_name')],
            [t(user_id, 'change_phone')],
            [t(user_id, 'back')]
        ]
        markup = ReplyKeyboardMarkup(btns, resize_keyboard=True)
        await update.message.reply_text(t(user_id, 'settings_menu'), reply_markup=markup)
        return SETTINGS_MENU
    else:
        await menu(update, context)
        return MAIN_MENU

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data and user_data[user_id].get("phone") and user_data[user_id].get("region"):
        await update.message.reply_text(t(user_id, 'ask_photo'), reply_markup=ReplyKeyboardRemove())
        return ASK_PHOTO
    contact_btn = KeyboardButton("Telefon raqamingizni ulashish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn], ["✍️ Qo‘lda kiritish"]], resize_keyboard=True)
    await update.message.reply_text(t(user_id, 'ask_phone'), reply_markup=markup)
    return ASK_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.contact:
        phone = update.message.contact.phone_number
        name = update.message.contact.first_name or ""
        user_data[user_id]["phone"] = phone
        user_data[user_id]["name"] = name
        markup = ReplyKeyboardMarkup(REGIONS, resize_keyboard=True)
        await update.message.reply_text(t(user_id, 'ask_region'), reply_markup=markup)
        return ASK_REGION
    elif update.message.text and "Qo‘lda kiritish" in update.message.text:
        await update.message.reply_text(t(user_id, 'enter_phone'), reply_markup=ReplyKeyboardRemove())
        return ENTER_PHONE
    else:
        await update.message.reply_text(t(user_id, 'ask_phone'), reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Telefon raqamingizni ulashish", request_contact=True)], ["✍️ Qo‘lda kiritish"]], resize_keyboard=True))
        return ASK_PHONE

async def handle_manual_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    name = update.effective_user.first_name or ""
    if not (phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit()):
        await update.message.reply_text(
            t(user_id, 'invalid_phone'),
            parse_mode="HTML"
        )
        return ENTER_PHONE
    user_data[user_id]["phone"] = phone
    user_data[user_id]["name"] = name
    markup = ReplyKeyboardMarkup(REGIONS, resize_keyboard=True)
    await update.message.reply_text(t(user_id, 'ask_region'), reply_markup=markup)
    return ASK_REGION

async def handle_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    region = update.message.text.strip()
    user_data[user_id]["region"] = region
    await update.message.reply_text(t(user_id, 'ask_photo'), reply_markup=ReplyKeyboardRemove())
    return ASK_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        try:
            with open("photo_note.mp4", "rb") as vnote:
                await context.bot.send_video_note(
                    chat_id=update.effective_chat.id,
                    video_note=vnote
                )
            await asyncio.sleep(2)
        except Exception as e:
            await update.message.reply_text(f"❗ Video yuborishda xato: {e}")
        await update.message.reply_text("📸 Iltimos, buyurtma uchun rasm yuboring.")
        return ASK_PHOTO
    photo_file_id = update.message.photo[-1].file_id
    user_data[user_id]["photo"] = photo_file_id
    await update.message.reply_text(t(user_id, 'ask_size'))
    return ASK_SIZE

async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    size = update.message.text.strip()
    user_data[user_id]["size"] = size
    data = user_data[user_id]
    order_info = {
        'name': data.get('name', ''),
        'phone': data.get('phone', ''),
        'region': data.get('region', ''),
        'size': data.get('size', ''),
        'date': datetime.now(pytz.timezone('Asia/Tashkent')).strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        write_to_sheets(order_info)
    except Exception as e:
        await update.message.reply_text(f"Google Sheets xatosi: {e}")

    photo = data.get("photo")
    text = t(user_id, 'new_order').format(
        name=order_info['name'],
        phone=order_info['phone'],
        region=order_info['region'],
        size=order_info['size'],
        date=order_info['date']
    )
    try:
        if photo:
            await context.bot.send_photo(
                chat_id=int(os.getenv("GROUP_CHAT_ID")),
                photo=photo,
                caption=text
            )
        else:
            await update.message.reply_text("❗ Rasm topilmadi, buyurtma guruhga yuborilmadi!")
    except Exception as e:
        await update.message.reply_text(f"Guruhga buyurtmani yuborishda xato: {e}")

    # Dumaloq video va 2 soniyadan keyin matn
    try:
        with open("success_note.mp4", "rb") as vnote:
            await context.bot.send_video_note(
                chat_id=update.effective_chat.id,
                video_note=vnote
            )
        await asyncio.sleep(2)
        await update.message.reply_text(
            t(user_id, 'order_success'),
            reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text(f"❗ Video yuborishda xato: {e}")

    return MAIN_MENU

async def settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if t(user_id, 'change_lang') in text:
        markup = ReplyKeyboardMarkup([[TEXTS['uz']['lang_uz'], TEXTS['uz']['lang_ru']]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(t(user_id, 'set_lang'), reply_markup=markup)
        return CHANGE_LANG
    elif t(user_id, 'change_region') in text:
        markup = ReplyKeyboardMarkup(REGIONS, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(t(user_id, 'set_region'), reply_markup=markup)
        return CHANGE_REGION
    elif t(user_id, 'change_name') in text:
        await update.message.reply_text(t(user_id, 'set_name'), reply_markup=ReplyKeyboardRemove())
        return CHANGE_NAME
    elif t(user_id, 'change_phone') in text:
        await update.message.reply_text(t(user_id, 'set_phone'), reply_markup=ReplyKeyboardRemove())
        return CHANGE_PHONE
    elif t(user_id, 'back') in text:
        await menu(update, context)
        return MAIN_MENU
    else:
        await menu(update, context)
        return MAIN_MENU

async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if 'O‘zbek' in text or 'O\'zbek' in text or 'Uzbek' in text:
        lang = 'uz'
    elif 'Русский' in text or 'Russian' in text:
        lang = 'ru'
    else:
        lang = get_lang(user_id)
    user_data[user_id]['lang'] = lang
    await update.message.reply_text(
        t(user_id, 'changed'),
        reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    )
    return MAIN_MENU

async def change_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    region = update.message.text.strip()
    user_data[user_id]['region'] = region
    await update.message.reply_text(
        t(user_id, 'changed'),
        reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    )
    return MAIN_MENU

async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()
    user_data[user_id]['name'] = name
    await update.message.reply_text(
        t(user_id, 'changed'),
        reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    )
    return MAIN_MENU

async def change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    if not (phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit()):
        await update.message.reply_text(
            t(user_id, 'invalid_phone'),
            parse_mode="HTML"
        )
        return CHANGE_PHONE
    user_data[user_id]['phone'] = phone
    await update.message.reply_text(
        t(user_id, 'changed'),
        reply_markup=ReplyKeyboardMarkup(t(user_id, 'menu_btns'), resize_keyboard=True)
    )
    return MAIN_MENU

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('menu', menu)
        ],
        states={
            CHECK_SUB: [MessageHandler(filters.ALL, lambda u, c: None)],  # bloklash uchun
            ASK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_lang)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_phone)],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region)],
            ASK_PHOTO: [MessageHandler(filters.PHOTO, handle_photo), MessageHandler(filters.ALL, handle_photo)],
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
    # MUHIM: callback uchun handler alohida qo'yiladi!
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_subscribe"))
    print("✅ Bot ishga tushdi, buyurtmalar va profil uchun tayyor!")
    app.run_polling()
