
import os
import json
import logging
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables to store user state
user_states = {}

def setup_google_sheets():
    """Setup Google Sheets connection"""
    try:
        # Get credentials from environment variable
        creds_json = os.getenv('GOOGLE_CREDS_JSON')
        if not creds_json:
            logger.error("GOOGLE_CREDS_JSON environment variable not found")
            return None
            
        # Parse the JSON credentials
        creds_dict = json.loads(creds_json)
        
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # Connect to Google Sheets
        gc = gspread.authorize(credentials)
        
        # Open the spreadsheet
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        if not spreadsheet_id:
            logger.error("SPREADSHEET_ID environment variable not found")
            return None
            
        sheet = gc.open_by_key(spreadsheet_id).sheet1
        return sheet
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error setting up Google Sheets: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    keyboard = [
        [KeyboardButton("🟢 Ishga keldim"), KeyboardButton("🔴 Ishdan ketdim")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Assalomu alaykum! Ishga kelish yoki ketishni belgilash uchun tugmani bosing:",
        reply_markup=reply_markup
    )

async def handle_work_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle work status buttons"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Store user state
    if "Ishga keldim" in text:
        user_states[user_id] = "came_to_work"
        await update.message.reply_text(
            "✅ 'Ishga keldim' belgilandi. Endi rasm yuboring."
        )
    elif "Ishdan ketdim" in text:
        user_states[user_id] = "left_work"
        await update.message.reply_text(
            "✅ 'Ishdan ketdim' belgilandi. Endi rasm yuboring."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Check if user has selected work status
    if user_id not in user_states:
        await update.message.reply_text(
            "❗️ Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing, keyin rasm yuboring."
        )
        return
    
    try:
        # Get current time in Tashkent timezone
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        current_time = datetime.now(tashkent_tz)
        
        # Prepare data for Google Sheets
        status = "Keldi" if user_states[user_id] == "came_to_work" else "Ketdi"
        
        # Setup Google Sheets
        sheet = setup_google_sheets()
        
        if sheet:
            try:
                # Add row to Google Sheets
                row_data = [
                    current_time.strftime("%Y-%m-%d"),  # Date
                    current_time.strftime("%H:%M:%S"),  # Time
                    f"{user.first_name} {user.last_name or ''}".strip(),  # Full name
                    user.username or "",  # Username
                    str(user_id),  # User ID
                    status,  # Status (Keldi/Ketdi)
                    "Rasm yuborildi"  # Photo status
                ]
                
                sheet.append_row(row_data)
                
                await update.message.reply_text(
                    f"✅ Ma'lumot muvaffaqiyatli saqlandi!\n"
                    f"📅 Sana: {current_time.strftime('%Y-%m-%d')}\n"
                    f"⏰ Vaqt: {current_time.strftime('%H:%M:%S')}\n"
                    f"👤 Foydalanuvchi: {user.first_name}\n"
                    f"📊 Status: {status}\n"
                    f"📸 Rasm: Qabul qilindi"
                )
                
            except Exception as e:
                logger.error(f"Error writing to Google Sheets: {e}")
                await update.message.reply_text(
                    f"❌ Google Sheets ga yozishda xatolik: {str(e)}\n"
                    f"Lekin Telegram ma'lumoti saqlab qolindi."
                )
        else:
            await update.message.reply_text(
                "❌ Google Sheets ulanishi o'rnatilmadi. Faqat Telegram ma'lumoti saqlandi."
            )
        
        # Send confirmation to group chat
        group_chat_id = os.getenv('GROUP_CHAT_ID')
        if group_chat_id:
            try:
                group_message = (
                    f"📋 Yangi ma'lumot:\n"
                    f"👤 {user.first_name} {user.last_name or ''}\n"
                    f"📅 {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"📊 {status}\n"
                    f"📸 Rasm qabul qilindi"
                )
                
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=group_message
                )
                
                # Forward the photo to group
                await context.bot.forward_message(
                    chat_id=group_chat_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                
            except Exception as e:
                logger.error(f"Error sending to group: {e}")
        
        # Clear user state
        del user_states[user_id]
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi: {str(e)}"
        )

def main():
    """Main function"""
    # Get bot token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable not found")
        return
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.Regex("🟢 Ishga keldim|🔴 Ishdan ketdim"), 
        handle_work_status
    ))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start the bot
    logger.info("Bot ishga tushmoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
