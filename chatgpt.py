import os
import openai
import telebot
from utils.db import is_premium, log_chat_session, get_user_memory, update_user_memory
from telebot.types import Message
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

MAX_FREE_TOKENS = 1000
MODEL_FREE = "gpt-3.5-turbo"
MODEL_PREMIUM = "gpt-4o"

# ✅ الرد التفاعلي (مثل ChatGPT)
def send_typing_effect(bot: telebot.TeleBot, chat_id: int, text: str):
    try:
        for i in range(0, len(text), 10):
            bot.send_chat_action(chat_id, "typing")
    except:
        pass

# ✅ معالجة المحادثة مع المستخدم
def handle_user_chat(bot: telebot.TeleBot, msg: Message):
    user_id = msg.from_user.id
    text = msg.text.strip()
    is_user_premium = is_premium(user_id)

    model = MODEL_PREMIUM if is_user_premium else MODEL_FREE

    # ✅ جلب سجل الجلسة السابق من الذاكرة (context)
    memory = get_user_memory(user_id)
    memory.append({"role": "user", "content": text})

    try:
        # ✅ إرسال تفاعل المستخدم (يكتب الآن...)
        send_typing_effect(bot, msg.chat.id, text)

        # ✅ طلب إلى OpenAI
        response = openai.ChatCompletion.create(
            model=model,
            messages=memory,
            temperature=0.7
        )

        reply = response.choices[0].message.content

        # ✅ تحديث الذاكرة + سجل الجلسة
        memory.append({"role": "assistant", "content": reply})
        update_user_memory(user_id, memory)
        log_chat_session(user_id, text, reply)

        bot.reply_to(msg, reply)

    except Exception as e:
        bot.reply_to(msg, f"❌ حدث خطأ أثناء المعالجة:
{e}")
        
