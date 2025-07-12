# main.py

import telebot
from config import BOT_TOKEN
from handlers.handlers import register_main_handlers, show_main_menu
from admin import register_admin_handlers
from chatgpt import handle_user_chat
from media_handlers.file_upload_handler import register_file_handler
from media_handlers.image_handler import register_image_handler
from media_handlers.audio_handler import register_audio_handler
from utils.db import register_user

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ✅ عرض رسالة بدء التشغيل
print("✅ تم تشغيل البوت بنجاح!")

# ✅ أمر /start لتسجيل المستخدم وعرض القائمة الرئيسية
@bot.message_handler(commands=['start'])
def handle_start(msg):
    try:
        register_user(msg.from_user)
        show_main_menu(bot, msg)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ حدث خطأ أثناء التشغيل: {e}")

# ✅ معالجة الرسائل النصية (GPT-3.5 أو GPT-4o حسب الاشتراك)
@bot.message_handler(func=lambda msg: True, content_types=['text'])
def handle_text(msg):
    try:
        handle_user_chat(bot, msg)
    except Exception as e:
        bot.send_message(msg.chat.id, "❌ عذرًا، حدث خطأ أثناء المعالجة.")

# ✅ تسجيل كافة الأقسام (Handlers)
register_main_handlers(bot)
register_admin_handlers(bot)
register_file_handler(bot)
register_image_handler(bot)
register_audio_handler(bot)

# ✅ تشغيل البوت باستمرار
bot.infinity_polling()