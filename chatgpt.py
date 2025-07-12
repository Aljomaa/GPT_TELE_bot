# chatgpt.py

import openai
from config import OPENAI_API_KEY
from utils.db import (
    is_premium, is_limited,
    increment_usage, get_chat_history,
    save_chat_history
)

openai.api_key = OPENAI_API_KEY

# ✅ التعامل مع رسالة المستخدم
def handle_user_chat(bot, msg):
    user_id = msg.from_user.id
    user_message = msg.text.strip()

    # ✅ التحقق من حالة الاشتراك
    premium = is_premium(user_id)
    limited = not premium and is_limited(user_id)

    if limited:
        bot.send_message(user_id, (
            "❌ لقد وصلت إلى الحد اليومي من الرسائل المجانية.\n\n"
            "🔓 اشترك في النسخة المميزة للحصول على محادثة غير محدودة مع GPT-4o.\n"
            "📩 راسل المشرف لتفعيل اشتراكك."
        ))
        return

    model = "gpt-4o" if premium else "gpt-3.5-turbo"

    try:
        # ✅ تحميل آخر 10 رسائل للمستخدم
        history = get_chat_history(user_id)[-10:]
        messages = history + [{"role": "user", "content": user_message}]

        # ✅ طلب رد من OpenAI
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()

        # ✅ إرسال الرد للمستخدم
        bot.send_message(
            user_id,
            f"🤖 <b>{model.upper()}</b>:\n{reply}",
            parse_mode="HTML"
        )

        # ✅ حفظ المحادثة
        save_chat_history(user_id, {"role": "user", "content": user_message})
        save_chat_history(user_id, {"role": "assistant", "content": reply})

        # ✅ تسجيل الاستخدام
        increment_usage(user_id, type="message")

    except Exception as e:
        print(f"[GPT ERROR]: {e}")
        bot.send_message(user_id, "❌ حدث خطأ أثناء الاتصال بـ GPT. حاول لاحقًا.")