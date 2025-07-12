# media_handlers/audio_handler.py

import os
import requests
import openai
import tempfile
import uuid
from telebot.types import Message
from config import OPENAI_API_KEY
from utils.db import is_premium, is_limited, increment_usage, log_audio
from chatgpt import ask_gpt
from gtts import gTTS

openai.api_key = OPENAI_API_KEY
TEMP_AUDIO_FOLDER = "temp_audio"

# تأكد من وجود مجلد مؤقت
if not os.path.exists(TEMP_AUDIO_FOLDER):
    os.makedirs(TEMP_AUDIO_FOLDER)

def register_audio_handler(bot):

    @bot.message_handler(content_types=['voice', 'audio'])
    def handle_audio(msg: Message):
        user_id = msg.from_user.id

        # تحقق من الحد المجاني
        if not is_premium(user_id) and is_limited(user_id):
            bot.reply_to(msg, "❌ لقد استهلكت الحد المجاني اليوم.\n🔐 اشترك للاستفادة غير المحدودة.")
            return

        try:
            # احصل على الملف الصوتي من تيليغرام
            file_id = msg.voice.file_id if msg.content_type == 'voice' else msg.audio.file_id
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            local_filename = f"{uuid.uuid4().hex}.mp3"
            local_path = os.path.join(TEMP_AUDIO_FOLDER, local_filename)

            # تحميل الملف
            url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
            r = requests.get(url)
            with open(local_path, 'wb') as f:
                f.write(r.content)

            # ترجمة الصوت إذا كتب المستخدم "ترجم"
            is_translate = "ترجم" in (msg.caption or "").lower()

            with open(local_path, "rb") as audio_file:
                transcript = (
                    openai.Audio.translate("whisper-1", audio_file)
                    if is_translate else
                    openai.Audio.transcribe("whisper-1", audio_file)
                )
                user_text = transcript["text"]

            # أرسل النص المستخرج
            bot.send_message(user_id, f"🎙️ تم تحويل الصوت إلى نص:\n<code>{user_text}</code>", parse_mode="HTML")

            # أرسل النص إلى GPT
            gpt_response = ask_gpt(user_id, user_text)

            # سجل الاستخدام + المحادثة
            increment_usage(user_id, "image")  # نستخدم image لحساب الصوت
            log_audio(user_id, user_text, gpt_response)

            # إنشاء صوت للرد باستخدام Google TTS
            tts = gTTS(text=gpt_response, lang='ar')
            audio_reply_path = os.path.join(TEMP_AUDIO_FOLDER, f"{uuid.uuid4().hex}_reply.mp3")
            tts.save(audio_reply_path)

            # أرسل الصوت
            with open(audio_reply_path, 'rb') as voice_msg:
                bot.send_audio(user_id, voice_msg, caption="🔊 الرد الصوتي من GPT")

        except Exception as e:
            print("⛔ ERROR audio_handler:", e)
            bot.reply_to(msg, "⚠️ حصل خطأ أثناء معالجة الملف الصوتي. جرب لاحقًا.")

        finally:
            # حذف الملفات المؤقتة
            if os.path.exists(local_path):
                os.remove(local_path)
            if 'audio_reply_path' in locals() and os.path.exists(audio_reply_path):
                os.remove(audio_reply_path)