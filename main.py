import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = -4786339709  # Guruh ID

# States for ConversationHandler
ASK_PHONE, ASK_REGION, ASK_PHOTO, ASK_SIZE = range(4)

# User data saqlanadi (RAMda)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Agar foydalanuvchi raqam va viloyatni avval kiritgan bo‘lsa, to‘g‘ridan-to‘g‘ri rasm bosqichiga o‘tkazamiz
    if user_id in user_data and user_data[user_id].get("phone") and user_data[user_id].get("region"):
        await update.message.reply_text("📸 Buyurtma uchun rasm yuboring:")
        return ASK_PHOTO

    # Agar faqat raqam kiritgan bo‘lsa, viloyat tanlashga o‘tkazamiz
    if user_id in user_data and user_data[user_id].get("phone"):
        return await ask_region(update, context)

    # Telefon raqam so‘raymiz
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn], ["✍️ Qo‘lda kiritish"]], resize_keyboard=True)
    await update.message.reply_text(
        "📞 Telefon raqamingizni ulashing yoki +998XXXXXXXXX tarzda qo‘lda kiriting:",
        reply_markup=markup
    )
    return ASK_PHONE

async def ask_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    viloyatlar = [
        ["Toshkent", "Andijon", "Farg‘ona"],
        ["Namangan", "Buxoro", "Jizzax"],
        ["Xorazm", "Qashqadaryo", "Samarqand"],
        ["Surxondaryo", "Sirdaryo", "Navoiy"],
        ["Qoraqalpog‘iston"]
    ]
    markup = ReplyKeyboardMarkup(viloyatlar, resize_keyboard=True)
    await update.message.reply_text(
        "📍 Viloyatingizni tanlang:", reply_markup=markup
    )
    return ASK_REGION

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
            await update.message.reply_text("❌ Telefon raqam formati xato. Namuna: +998889000232")
            return ASK_PHONE

    # Ma’lumotlarni saqlash (agar oldin kiritilgan bo‘lsa yangilanmaydi)
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["phone"] = phone
    user_data[user_id]["name"] = name

    return await ask_region(update, context)

async def handle_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    region = update.message.text.strip()
    user_data[user_id]["region"] = region
    await update.message.reply_text("📸 Buyurtma uchun rasm yuboring:")
    return ASK_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file_id = update.message.photo[-1].file_id
    user_data[user_id]["photo"] = photo_file_id
    await update.message.reply_text("📏 O‘lchamingizni kiriting:")
    return ASK_SIZE

async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    size = update.message.text.strip()
    user_data[user_id]["size"] = size

    # Buyurtma haqida ma'lumotni guruhga yuboramiz
    data = user_data[user_id]
    text = (
        f"🆕 Yangi buyurtma!\n"
        f"👤 Ism: {data.get('name', 'Noma’lum')}\n"
        f"📞 Tel: {data.get('phone', 'Noma’lum')}\n"
        f"📍 Viloyat: {data.get('region', 'Noma’lum')}\n"
        f"📏 O‘lcham: {data.get('size', '')}\n"
        f"🕰 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await context.bot.send_photo(
        chat_id=GROUP_CHAT_ID,
        photo=data["photo"],
        caption=text
    )
    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi! Yangi buyurtma uchun /start ni bosing.")
    return ConversationHandler.END

# Qo‘lda telefon kiritish
async def manual_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_phone(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
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
