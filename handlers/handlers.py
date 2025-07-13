# handlers/handlers.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from chatgpt import handle_user_chat
from admin import show_admin_panel
from utils.db import register_user, is_premium

# ✅ عرض القائمة الرئيسية
def show_main_menu(bot, message):
    user_id = message.from_user.id
    register_user(message.from_user)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("💬 اسأل ChatGPT", callback_data="gpt:start"))

    # ✅ زر المشرف للمالك فقط
    if user_id == OWNER_ID:
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="admin:panel"))

    bot.send_message(
        message.chat.id,
        "👋 مرحبًا بك في بوت الذكاء الاصطناعي!\nاختر من الأزرار أدناه:",
        reply_markup=markup
    )

# ✅ تسجيل جميع الأوامر والأزرار
def register_handlers(bot):

    @bot.message_handler(commands=['start'])
    def handle_start(msg):
        show_main_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data == "back")
    def handle_back(call):
        show_main_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data == "gpt:start")
    def handle_gpt_start(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✍️ أرسل الآن سؤالك إلى ChatGPT...")
        bot.register_next_step_handler(call.message, lambda msg: handle_user_chat(bot, msg))

    @bot.callback_query_handler(func=lambda call: call.data == "admin:panel")
    def handle_admin_panel(call):
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ غير مصرح", show_alert=True)
            return
        show_admin_panel(bot, call.message)
