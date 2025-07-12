# admin.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from utils.db import activate_premium
import telebot

# تخزين حالة التفعيل المؤقتة
pending_activation = {}

def show_admin_panel(bot: telebot.TeleBot, message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ تفعيل اشتراك لمستخدم", callback_data="admin:activate"))
    markup.add(InlineKeyboardButton("⬅️ رجوع", callback_data="back"))
    
    bot.edit_message_text("🧑‍💼 لوحة المشرف:\nاختر ما تريد تنفيذه:", message.chat.id, message.message_id, reply_markup=markup)

def register_admin_handlers(bot: telebot.TeleBot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin:"))
    def handle_admin_buttons(call):
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ هذه القائمة خاصة بالمشرف فقط", show_alert=True)
            return

        action = call.data.split(":")[1]
        msg_id = call.message.message_id

        if action == "activate":
            bot.edit_message_text("👤 أرسل لي الآن رقم ID المستخدم الذي تريد تفعيل الاشتراك له:", call.message.chat.id, msg_id)
            pending_activation[call.message.chat.id] = "awaiting_user_id"
            bot.register_next_step_handler(call.message, process_user_id)

def process_user_id(msg):
    chat_id = msg.chat.id

    if pending_activation.get(chat_id) != "awaiting_user_id":
        return

    try:
        user_id = int(msg.text.strip())
    except ValueError:
        msg.bot.send_message(chat_id, "❌ الرقم غير صالح. أعد المحاولة.")
        return

    activate_premium(user_id)
    msg.bot.send_message(chat_id, f"✅ تم تفعيل الاشتراك لمدة شهر للمستخدم:\n<code>{user_id}</code>", parse_mode="HTML")
    pending_activation.pop(chat_id, None)