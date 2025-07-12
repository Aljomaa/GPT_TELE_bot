# utils/db.py

from pymongo import MongoClient
from datetime import datetime, timedelta
from config import OWNER_ID
import os

# إعداد الاتصال بقاعدة البيانات
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["gpt_telegram_bot"]

user_col = db["users"]
premium_col = db["premium"]

# ✅ تسجيل المستخدم
def register_user(user):
    user_id = user.id if hasattr(user, 'id') else user
    if not user_col.find_one({"_id": user_id}):
        user_col.insert_one({
            "_id": user_id,
            "name": user.full_name if hasattr(user, 'full_name') else "",
            "username": user.username if hasattr(user, 'username') else "",
            "joined": datetime.utcnow(),
            "usage": {
                "message": 0,
                "image": 0,
                "date": datetime.utcnow().date().isoformat()
            },
            "history": []
        })

# ✅ فحص الاشتراك المميز وإلغاء المنتهي تلقائيًا
def is_premium(user_id):
    record = premium_col.find_one({"_id": user_id})
    if record and record.get("expires"):
        if datetime.utcnow() < record["expires"]:
            return True
        else:
            # تم انتهاء الاشتراك نحذفه
            premium_col.delete_one({"_id": user_id})
    return False

# ✅ تفعيل اشتراك مميز لمدة شهر
def activate_premium(user_id):
    expires = datetime.utcnow() + timedelta(days=30)
    premium_col.update_one(
        {"_id": user_id},
        {"$set": {"expires": expires}},
        upsert=True
    )

# ✅ إلغاء الاشتراك يدويًا
def deactivate_premium(user_id):
    premium_col.delete_one({"_id": user_id})

# ✅ التحقق من المالك
def is_owner(user_id):
    return user_id == OWNER_ID

# ✅ التحقق من تجاوز الحد المجاني
def is_limited(user_id):
    today = datetime.utcnow().date().isoformat()
    user = user_col.find_one({"_id": user_id})

    if user:
        usage = user.get("usage", {})
        if usage.get("date") != today:
            reset_daily_usage(user_id)
            return False

        return usage.get("message", 0) >= 10 or usage.get("image", 0) >= 1
    return True

# ✅ إعادة تعيين العداد اليومي
def reset_daily_usage(user_id):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {
            "usage": {
                "message": 0,
                "image": 0,
                "date": datetime.utcnow().date().isoformat()
            }
        }}
    )

# ✅ تسجيل الاستخدام اليومي
def increment_usage(user_id, type="message"):
    today = datetime.utcnow().date().isoformat()
    user = user_col.find_one({"_id": user_id})

    if user:
        usage = user.get("usage", {})
        if usage.get("date") != today:
            reset_daily_usage(user_id)

        field = f"usage.{type}"
        user_col.update_one(
            {"_id": user_id},
            {"$inc": {field: 1}, "$set": {"usage.date": today}}
        )

# ✅ حفظ سجل المحادثة (آخر 20 فقط)
def save_chat_history(user_id, user_msg, gpt_response):
    user = user_col.find_one({"_id": user_id})
    if not user:
        return
    history = user.get("history", [])
    history.append({
        "q": user_msg,
        "a": gpt_response,
        "time": datetime.utcnow()
    })
    if len(history) > 20:
        history = history[-20:]
    user_col.update_one(
        {"_id": user_id},
        {"$set": {"history": history}}
    )

# ✅ سجل تحليلات الصوت
def log_audio(user_id, transcription, answer):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {
            "audio_logs": {
                "transcription": transcription,
                "answer": answer,
                "time": datetime.utcnow()
            }
        }}
    )

# ✅ سجل تحليلات الصور
def log_image_analysis(user_id, image_result):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {
            "image_logs": {
                "result": image_result,
                "time": datetime.utcnow()
            }
        }}
    )

# ✅ سجل تحليلات الملفات
def log_file_analysis(user_id, filename, result):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {
            "file_logs": {
                "filename": filename,
                "response": result,
                "timestamp": datetime.utcnow()
            }
        }}
    )

# ✅ إحصائيات المشرف
def get_stats():
    total_users = user_col.count_documents({})
    premium_users = premium_col.count_documents({})
    return total_users, premium_users