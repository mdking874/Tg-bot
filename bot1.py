import requests
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = "8820220763:AAHJba4Pf-AUa2Foa-kgqDdCyCRkdbQ49rs"

FIREBASE_DB_URL = "https://bkhot-5f82a-default-rtdb.firebaseio.com"

VIDEOS_URL = f"{FIREBASE_DB_URL}/videos.json"
HISTORY_URL = f"{FIREBASE_DB_URL}/history.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


# ==============================
# FIREBASE HISTORY MANAGEMENT
# ==============================

def get_firebase_history():
    """ফায়ারবেজ থেকে সব ইউজারের হিস্ট্রি আনবে"""
    try:
        response = requests.get(HISTORY_URL, timeout=15)
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print("Firebase History Load Error:", e)
        return {}

def save_user_history_to_firebase(user_id, new_records):
    """ইউজারের হিস্ট্রি ফায়ারবেজে আপডেট করবে (৭ দিনের ফিল্টারসহ)"""
    try:
        user_str = str(user_id)
        history_data = get_firebase_history()
        
        user_records = history_data.get(user_str, [])
        if not isinstance(user_records, list):
            user_records = []
            
        now = datetime.now()
        
        # ৭ দিনের পুরানো রেকর্ড বাদ দেওয়া
        valid_records = []
        for rec in user_records:
            if isinstance(rec, dict) and "time" in rec:
                try:
                    rec_time = datetime.fromisoformat(rec["time"])
                    if now - rec_time < timedelta(days=7):
                        valid_records.append(rec)
                except:
                    pass
                    
        # নতুন ভিডিওগুলোর রেকর্ড যোগ করা
        for vid in new_records:
            valid_records.append({"id": vid, "time": now.isoformat()})
            
        # ফায়ারবেজে নির্দিষ্ট ইউজারের ডাটা প্যাচ (PATCH) করা
        requests.patch(f"{FIREBASE_DB_URL}/history.json", json={user_str: valid_records}, timeout=15)
    except Exception as e:
        print("Firebase History Save Error:", e)

def get_user_seen_ids(user_id):
    """ইউজার গত ৭ দিনে যে ভিডিওগুলো দেখেছে সেগুলোর আইডি রিটার্ন করবে"""
    try:
        history_data = get_firebase_history()
        user_str = str(user_id)
        user_records = history_data.get(user_str, [])
        
        if not isinstance(user_records, list):
            return []
            
        now = datetime.now()
        seen_ids = []
        for rec in user_records:
            if isinstance(rec, dict) and "time" in rec and "id" in rec:
                try:
                    rec_time = datetime.fromisoformat(rec["time"])
                    if now - rec_time < timedelta(days=7):
                        seen_ids.append(str(rec["id"]))
                except:
                    pass
        return seen_ids
    except Exception as e:
        print("Get Seen IDs Error:", e)
        return []


# ==============================
# FIREBASE DATA LOAD (VIDEOS)
# ==============================

def get_videos():
    try:
        response = requests.get(VIDEOS_URL, timeout=15)
        data = response.json()

        if isinstance(data, dict):
            video_list = []
            for k, v in data.items():
                if isinstance(v, dict):
                    v["id"] = v.get("id", k)
                    video_list.append(v)
            return video_list

        elif isinstance(data, list):
            return [v for v in data if isinstance(v, dict)]

        return []
    except Exception as e:
        print("Firebase Videos Error:", e)
        return []


# ==============================
# 20 RANDOM VIDEOS (Filtering 7 days)
# ==============================

def get_20_random_videos(user_id):
    videos = get_videos()
    if not videos:
        return []

    seen_ids = get_user_seen_ids(user_id)
    
    # ৭ দিনের মধ্যে দেখা হয়নি এমন ভিডিওগুলো ফিল্টার করা
    available_videos = [v for v in videos if str(v.get("id", "")) not in seen_ids]

    # যদি পর্যাপ্ত নতুন ভিডিও না থাকে, তবে সব ভিডিও থেকে রেন্ডমলি নেওয়া শুরু করবে
    if len(available_videos) < 20:
        available_videos = videos

    # রেন্ডমলি ২০টি ভিডিও সিলেক্ট করা (যদি ২০টি বা তার কম থাকে তবে সবগুলোই দিবে)
    selected = random.sample(available_videos, min(20, len(available_videos)))
    
    # সিলেক্ট করা ভিডিওগুলোর আইডি ফায়ারবেজ হিস্ট্রিতে সেভ করা
    selected_ids = [str(v.get("id", "")) for v in selected if v.get("id")]
    save_user_history_to_firebase(user_id, selected_ids)

    return selected


# ==============================
# START COMMAND
# ==============================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "🎬 Video Bot চালু আছে\n\n"
        "একসাথে ২০টি ভিডিও পেতে লিখুন:\n"
        "/video"
    )


# ==============================
# VIDEO COMMAND (20 Videos)
# ==============================

@dp.message_handler(commands=["video"])
async def video(message: types.Message):
    user_id = message.from_user.id
    videos = get_20_random_videos(user_id)

    if not videos:
        await message.reply("❌ কোনো ভিডিও পাওয়া যায়নি")
        return

    await message.reply(f"🎬 আপনার জন্য রেন্ডম **{len(videos)}টি** ভিডিও নিচে দেওয়া হলো:")

    for data in videos:
        title = data.get("title", "No Title")
        thumb = data.get("thumb")
        url = data.get("url")
        category = data.get("category", "Unknown")
        video_id = data.get("id", "")

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                text="▶️ PLAY VIDEO",
                url=url
            )
        )

        caption = (
            f"🎬 **{title}**\n"
            f"📂 Category: {category}\n"
            f"🆔 ID: {video_id}"
        )

        try:
            if thumb:
                await message.answer_photo(
                    photo=thumb,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await message.reply(
                    caption,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Message send error: {e}")


# ==============================
# RUN BOT
# ==============================

if __name__ == "__main__":
    print("Bot Started...")
    executor.start_polling(dp, skip_updates=True)
