# handlers/handlers.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from chatgpt import handle_user_chat
from admin import show_admin_panel
from utils.db import register_user, is_premium, premium_col
from datetime import datetime

# ✅ عرض القائمة الرئيسية
def show_main_menu(bot, message):
    user_id = message.from_user.id
    register_user(message.from_user)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("💬 اسأل ChatGPT", callback_data="gpt:start"))
    markup.add(InlineKeyboardButton("⭐ حالتي", callback_data="gpt:status"))

    # زر المشرف يظهر فقط للمالك
    if user_id == OWNER_ID:
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="admin:panel"))

    bot.send_message(
        message.chat.id,
        "👋 <b>مرحبًا بك في بوت ChatGPT الذكي!</b>\n\n"
        "🔹 استخدم الأزرار للتفاعل مع الذكاء الاصطناعي.\n"
        "🔸 المجانيون: 10 رسائل و1 صورة يوميًا.\n"
        "✨ اشترك لتجربة غير محدودة مع GPT-4o.",
        parse_mode="HTML",
        reply_markup=markup
    )

# ✅ تسجيل الأزرار والردود
def register_main_handlers(bot):

    @bot.message_handler(commands=['start'])
    def handle_start(msg):
        show_main_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data == "back")
    def handle_back(call):
        show_main_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data == "gpt:start")
    def handle_gpt_start(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✍️ أرسل سؤالك الآن إلى ChatGPT...")
        bot.register_next_step_handler(call.message, lambda msg: handle_user_input(bot, msg))

    @bot.callback_query_handler(func=lambda call: call.data == "gpt:status")
    def handle_gpt_status(call):
        user_id = call.from_user.id
        if is_premium(user_id):
            record = premium_col.find_one({"_id": user_id})
            expires = record.get("expires")
            date_text = expires.strftime("%Y-%m-%d") if expires else "❓"
            text = f"✅ أنت مشترك بنسخة <b>مميزة</b>\n⏳ ينتهي الاشتراك في: <b>{date_text}</b>"
        else:
            text = "⚠️ أنت تستخدم النسخة <b>المجانية</b>\n\nيمكنك استخدام 10 رسائل و1 صورة يوميًا فقط."

        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML",
                              reply_markup=InlineKeyboardMarkup().add(
                                  InlineKeyboardButton("⬅️ رجوع", callback_data="back")
                              ))

    @bot.callback_query_handler(func=lambda call: call.data == "admin:panel")
    def handle_admin_panel(call):
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ غير مصرح لك بالدخول", show_alert=True)
            return
        show_admin_panel(bot, call.message)

# ✅ التحقق من الإدخال الفعلي قبل إرساله إلى GPT
def handle_user_input(bot, msg):
    if not msg.text:
        bot.send_message(msg.chat.id, "❌ الرجاء إرسال نص فقط.")
        bot.register_next_step_handler(msg, lambda m: handle_user_input(bot, m))
        return

    handle_user_chat(bot, msg)