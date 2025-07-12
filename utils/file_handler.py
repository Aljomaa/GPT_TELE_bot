import os
import io
import json
import telebot
import pandas as pd
import pdfplumber
from telebot.types import Message
from utils.db import is_premium, log_file_analysis
from deep_translator import GoogleTranslator
from docx import Document
from bs4 import BeautifulSoup
from pptx import Presentation

MAX_FREE_SIZE_MB = 2
MAX_PREMIUM_SIZE_MB = 20

def register_file_handler(bot: telebot.TeleBot):

    @bot.message_handler(content_types=['document'])
    def handle_file(msg: Message):
        user_id = msg.from_user.id
        file_info = bot.get_file(msg.document.file_id)
        file_size = msg.document.file_size / (1024 * 1024)  # Convert to MB
        is_user_premium = is_premium(user_id)

        size_limit = MAX_PREMIUM_SIZE_MB if is_user_premium else MAX_FREE_SIZE_MB
        if file_size > size_limit:
            bot.reply_to(msg, f"❌ الحد الأقصى لحجم الملف هو {size_limit}MB")
            return

        try:
            downloaded_file = bot.download_file(file_info.file_path)
            filename = msg.document.file_name.lower()
            content = extract_content(downloaded_file, filename)

            if not content.strip():
                bot.reply_to(msg, "❌ لم أتمكن من استخراج أي محتوى من الملف.")
                return

            content = content[:2000]  # Telegram character limit
            translated = GoogleTranslator(source='auto', target='ar').translate(text=content)
            bot.reply_to(msg, f"📄 <b>محتوى الملف:</b>\n<pre>{translated}</pre>", parse_mode="HTML")
            log_file_analysis(user_id, filename)

        except Exception as e:
            bot.reply_to(msg, f"❌ حدث خطأ أثناء قراءة الملف: {e}")

def extract_content(file_bytes, filename):
    content = ""
    stream = io.BytesIO(file_bytes)

    if filename.endswith(".pdf"):
        with pdfplumber.open(stream) as pdf:
            for page in pdf.pages:
                content += page.extract_text() or ''

    elif filename.endswith(".docx"):
        doc = Document(stream)
        for para in doc.paragraphs:
            content += para.text + "\n"

    elif filename.endswith(".txt"):
        content = stream.read().decode("utf-8", errors="ignore")

    elif filename.endswith(".csv") or filename.endswith(".xlsx"):
        df = pd.read_csv(stream) if filename.endswith(".csv") else pd.read_excel(stream)
        content = df.to_string()

    elif filename.endswith(".json"):
        data = json.load(stream)
        content = json.dumps(data, indent=2, ensure_ascii=False)

    elif filename.endswith(".html"):
        soup = BeautifulSoup(stream.read(), "html.parser")
        content = soup.get_text()

    elif filename.endswith(".pptx"):
        prs = Presentation(stream)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    content += shape.text + "\n"

    return content
