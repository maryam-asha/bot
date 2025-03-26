import os
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def create_menu():
    # Create a list of button rows
    keyboard = [
        [KeyboardButton("حول المنصة")],
        [KeyboardButton("حول الوزارة")],
        [KeyboardButton("حول الشركة المطورة")],
        [KeyboardButton("سمعنا صوتك")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text= "مرحباََ بك في منصة صوتك",
        reply_markup=create_menu()
    )

def handle_message(update, context):
    response = {
        "حول المنصة": "منصة صوتك هي المنصة الأولى للمواطنين للتعبير عن آرائهم ومقترحاتهم وتقديم شكاويهم في كل المواضيع والخدمات والجهات العاملة تحت وزارة التقانة والاتصالات للجمهورية العربية السورية وقريباً في جميع الوزارات",
        "حول الوزارة": "",
        "حول الشركة المطورة": "",
        "سمعنا صوتك": "Coming Soon",
    }.get(update.message.text, "يرجى اختيار خيار من القائمة.")
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        reply_markup=create_menu()
    )

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()