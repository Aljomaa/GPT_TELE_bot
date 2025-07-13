import os
import uuid
import requests
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import OPENAI_API_KEY
from utils.db import is_premium, is_limited, increment_usage, log_image_analysis
from chatgpt import ask_gpt
from gtts import gTTS
import pytesseract
from PIL import Image
from deep_translator import GoogleTranslator

TEMP_IMG_FOLDER = "temp_images"
os.makedirs(TEMP_IMG_FOLDER, exist_ok=True)

def register_image_handler(bot):
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_image(msg: Message):
        user_id = msg.from_user.id

        # تحقق من حدود الاستخدام
        if not is_premium(user_id) and is_limited(user_id):
            bot.reply_to(msg, "❌ لقد استهلكت الحد المجاني اليوم.\n🔐 اشترك للاستفادة غير المحدودة.")
            return

        try:
            bot.send_chat_action(user_id, "upload_photo")

            # تحميل الصورة سواء أُرسلت كـ photo أو document
            file_id = msg.photo[-1].file_id if msg.content_type == 'photo' else msg.document.file_id
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            img_name = f"{uuid.uuid4().hex}.jpg"
            local_path = os.path.join(TEMP_IMG_FOLDER, img_name)

            img_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
            r = requests.get(img_url)
            with open(local_path, 'wb') as f:
                f.write(r.content)

            extracted_text = extract_text_from_image(local_path)
            gpt_response = ask_gpt(user_id, f"صف لي هذه الصورة:\n{extracted_text}")
            translated_response = translate_to_arabic_if_needed(gpt_response)

            increment_usage(user_id, "image")
            log_image_analysis(user_id, extracted_text, translated_response)

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔁 تحليل مجددًا", callback_data=f"image:reprocess:{img_name}"))

            bot.send_message(user_id, f"🖼️ <b>تحليل الصورة:</b>\n<code>{translated_response}</code>", 
                             parse_mode="HTML", reply_markup=markup)

            voice_path = os.path.join(TEMP_IMG_FOLDER, f"{uuid.uuid4().hex}_reply.mp3")
            tts = gTTS(text=translated_response, lang='ar')
            tts.save(voice_path)

            with open(voice_path, 'rb') as voice_file:
                bot.send_audio(user_id, voice_file, caption="🔊 الرد الصوتي على الصورة")

        except Exception as e:
            print("❌ ERROR in image_handler:", e)
            bot.reply_to(msg, "⚠️ حدث خطأ أثناء معالجة الصورة. جرب لاحقًا.")

        finally:
            if os.path.exists(local_path): os.remove(local_path)
            if 'voice_path' in locals() and os.path.exists(voice_path): os.remove(voice_path)

# ✅ OCR: استخراج النصوص من الصورة
def extract_text_from_image(path):
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+ara")
        return text.strip()
    except Exception as e:
        print("OCR error:", e)
        return "صورة بدون نص واضح."

# ✅ ترجمة للغة العربية إذا لزم
def translate_to_arabic_if_needed(text):
    try:
        if any(c.isalpha() for c in text) and not any('\u0600' <= c <= '\u06FF' for c in text):
            return GoogleTranslator(source='auto', target='ar').translate(text)
        return text
    except:
        return text
