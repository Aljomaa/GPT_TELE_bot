# media_handlers/file_upload_handler.py

import os
import uuid
import requests
from telebot.types import Message
from utils.db import is_premium, is_limited, increment_usage, log_file_analysis
from utils.extractor import extract_text_from_file
from chatgpt import ask_gpt
from gtts import gTTS
from deep_translator import GoogleTranslator

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

def register_file_handler(bot):

    @bot.message_handler(content_types=['document'])
    def handle_file(msg: Message):
        user_id = msg.from_user.id

        if not is_premium(user_id) and is_limited(user_id):
            bot.reply_to(msg, "❌ لقد استهلكت الحد المجاني اليوم.\n🔐 اشترك للاستفادة غير المحدودة.")
            return

        try:
            bot.send_chat_action(user_id, "upload_document")
            file_info = bot.get_file(msg.document.file_id)
            file_path = file_info.file_path
            file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

            local_filename = f"{uuid.uuid4().hex}_{msg.document.file_name}"
            local_path = os.path.join(TEMP_DIR, local_filename)

            # تحميل الملف
            response = requests.get(file_url)
            with open(local_path, 'wb') as f:
                f.write(response.content)

            # استخراج النص
            extracted_text = extract_text_from_file(local_path)

            if not extracted_text.strip():
                bot.send_message(user_id, "⚠️ لم أتمكن من استخراج نص مفيد من هذا الملف.")
                return

            # تحديد النموذج والرد المناسب
            prompt = f"اقرأ هذا النص وحلله أو لخّصه أو استخرج منه الفوائد:\n\n{extracted_text[:3000]}"
            gpt_response = ask_gpt(user_id, prompt)

            # ترجمة للغة العربية إذا لزم
            translated_response = translate_to_arabic_if_needed(gpt_response)

            # سجل الاستخدام
            increment_usage(user_id, "message")
            log_file_analysis(user_id, msg.document.file_name, extracted_text, translated_response)

            # إرسال الرد النصي
            role_text = "🟢 مستخدم مميز" if is_premium(user_id) else "🔵 مستخدم مجاني"
            bot.send_message(
                user_id,
                f"📄 تم تحليل الملف: <b>{msg.document.file_name}</b>\n\n{translated_response}",
                parse_mode="HTML"
            )

            # تحويل الرد إلى صوت
            voice_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_reply.mp3")
            tts = gTTS(text=translated_response, lang='ar')
            tts.save(voice_path)

            with open(voice_path, 'rb') as voice_file:
                bot.send_audio(user_id, voice_file, caption="🎧 الرد الصوتي على الملف")

        except Exception as e:
            print("❌ ERROR in file_handler:", e)
            bot.reply_to(msg, "⚠️ حدث خطأ أثناء تحليل الملف. حاول لاحقًا.")

        finally:
            if os.path.exists(local_path): os.remove(local_path)
            if 'voice_path' in locals() and os.path.exists(voice_path): os.remove(voice_path)

# ✅ الترجمة للغة العربية (إن لم يكن النص أصلاً بالعربية)
def translate_to_arabic_if_needed(text):
    try:
        if any(c.isalpha() for c in text) and not any('\u0600' <= c <= '\u06FF' for c in text):
            return GoogleTranslator(source='auto', target='ar').translate(text)
        return text
    except:
        return text