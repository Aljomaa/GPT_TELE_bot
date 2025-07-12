# vision.py

import base64
import requests
import io
from PIL import Image
from datetime import datetime
import openai
from config import OPENAI_API_KEY
from utils.db import is_premium, log_image_analysis
from deep_translator import GoogleTranslator
import pytesseract

openai.api_key = OPENAI_API_KEY

# ✅ ضغط الصورة لتقليل الحجم
def compress_image(img_bytes, max_size=(1024, 1024)):
    image = Image.open(io.BytesIO(img_bytes))
    image.thumbnail(max_size)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=80)
    return output.getvalue()

# ✅ تحويل الصورة إلى base64
def encode_image_base64(img_bytes):
    return base64.b64encode(img_bytes).decode('utf-8')

# ✅ استخراج النص داخل الصورة باستخدام OCR
def extract_text_ocr(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(img, lang='eng+ara')
    except:
        return ""

# ✅ ترجمة إنجليزية → عربية إذا لزم
def translate_to_arabic_if_needed(text):
    try:
        if any(c.isalpha() for c in text) and not any('\u0600' <= c <= '\u06FF' for c in text):
            return GoogleTranslator(source='auto', target='ar').translate(text)
        return text
    except:
        return text

# ✅ تحليل الصورة باستخدام GPT-4o Vision
def analyze_image(user_id, image_bytes, file_name="صورة"):

    # ضغط وتحويل Base64
    compressed = compress_image(image_bytes)
    base64_image = encode_image_base64(compressed)

    # إعداد النموذج
    prompt = "حلل هذه الصورة بالتفصيل وأخبرني بما تحتويه باحتراف. إذا كان فيها نص، صفه أيضًا."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "أنت مساعد خبير في تحليل الصور."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.5,
            max_tokens=1500
        )

        gpt_response = response.choices[0].message["content"]
        translated = translate_to_arabic_if_needed(gpt_response)

        # OCR
        extracted_text = extract_text_ocr(image_bytes)
        if extracted_text.strip():
            translated_text = translate_to_arabic_if_needed(extracted_text)
            translated += f"\n\n🧾 نص داخل الصورة:\n{translated_text}"

        # سجل التحليل
        log_image_analysis(user_id, file_name, translated)

        return translated

    except Exception as e:
        print("❌ GPT Vision Error:", e)
        return "⚠️ حدث خطأ أثناء تحليل الصورة."