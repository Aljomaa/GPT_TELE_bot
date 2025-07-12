# media_handlers/file_handler.py

import os
import io
import json
import pandas as pd
import fitz  # PyMuPDF
import docx
import openai
from bs4 import BeautifulSoup
from pptx import Presentation
from telebot.types import Message
from config import OPENAI_API_KEY
from utils.db import is_premium, log_file_analysis
from deep_translator import GoogleTranslator

openai.api_key = OPENAI_API_KEY
MAX_FREE_SIZE_MB = 2
MAX_PREMIUM_SIZE_MB = 20

def translate_if_needed(text):
    try:
        if any(c.isalpha() for c in text) and not any('\u0600' <= c <= '\u06FF' for c in text):
            return GoogleTranslator(source='auto', target='ar').translate(text)
    except:
        return text
    return text

def read_pdf(file_stream):
    try:
        doc = fitz.open(stream=file_stream, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text.strip()
    except:
        return ""

def read_docx(file_stream):
    try:
        doc = docx.Document(file_stream)
        return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""

def read_txt(file_stream):
    return file_stream.read().decode('utf-8', errors='ignore')

def read_csv_excel(file_stream, ext):
    try:
        if ext == "csv":
            df = pd.read_csv(file_stream)
        else:
            df = pd.read_excel(file_stream)
        return df.to_markdown(index=False)
    except:
        return ""

def read_json(file_stream):
    try:
        data = json.load(file_stream)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except:
        return ""

def read_html(file_stream):
    try:
        soup = BeautifulSoup(file_stream.read(), 'html.parser')
        return soup.get_text(separator="\n").strip()
    except:
        return ""

def read_pptx(file_stream):
    try:
        prs = Presentation(file_stream)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    except:
        return ""

def handle_uploaded_file(bot, message: Message, file_info):
    user_id = message.from_user.id
    premium = is_premium(user_id)
    file_size = file_info.file_size / (1024 * 1024)
    max_size = MAX_PREMIUM_SIZE_MB if premium else MAX_FREE_SIZE_MB

    if file_size > max_size:
        bot.reply_to(message, f"⚠️ الحد الأقصى للملف {'(20MB للمميز)' if premium else '(2MB للمجاني)'} تم تجاوزه.")
        return

    file_id = file_info.file_id
    file_name = file_info.file_path.split("/")[-1]
    ext = file_name.split(".")[-1].lower()

    file_path = os.path.join("/mnt/data/temp_files", file_name)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    try:
        with open(file_path, 'rb') as f:
            file_stream = io.BytesIO(f.read())

        if ext == "pdf":
            content = read_pdf(file_stream)
        elif ext == "docx":
            content = read_docx(file_stream)
        elif ext == "txt":
            content = read_txt(file_stream)
        elif ext in ["csv", "xls", "xlsx"]:
            content = read_csv_excel(file_stream, ext)
        elif ext == "json":
            content = read_json(file_stream)
        elif ext in ["html", "htm"]:
            content = read_html(file_stream)
        elif ext in ["pptx"]:
            content = read_pptx(file_stream)
        else:
            bot.reply_to(message, "❌ نوع الملف غير مدعوم حاليًا.")
            return

        if not content.strip():
            bot.reply_to(message, "⚠️ الملف لا يحتوي على نص قابل للقراءة.")
            return

        translated = translate_if_needed(content)

        log_file_analysis(user_id, file_name, translated)

        bot.send_message(
            message.chat.id,
            f"📄 <b>اسم الملف:</b> <code>{file_name}</code>\n\n📑 <b>المحتوى:</b>\n\n{translated[:4000]}",
            parse_mode="HTML"
        )

    except Exception as e:
        print("❌ File Handling Error:", e)
        bot.reply_to(message, "❌ حدث خطأ أثناء قراءة الملف.")