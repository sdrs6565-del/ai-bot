import os
import logging
import asyncio
import sqlite3
import urllib.parse
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from groq import Groq

# 1. LOGGING
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UltimateDownloaderBot")

# 2. SOZLAMALAR
# Render interfeysida ushbu o'zgaruvchilarni sozlashni unutmang
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("BOT_TOKEN va GROQ_API_KEY ni sozlash shart!")

bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)
groq_client = Groq(api_key=GROQ_API_KEY)

# 3. MA'LUMOTLAR BAZASI
DB_FILE = "ultimate_bot.db"

def execute_db(query: str, params: Tuple = ()):
    conn = sqlite3.connect(DB_FILE, timeout=20.0)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Baza xatoligi: {e}")
        return []
    finally:
        conn.close()

execute_db("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        msg_count INTEGER DEFAULT 0,
        joined_at TEXT
    )
""")

def save_user(user_id: int, username: str):
    exists = execute_db("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not exists:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db("INSERT INTO users (user_id, username, joined_at) VALUES (?, ?, ?)", (user_id, username, now))
    execute_db("UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?", (user_id,))

# 4. CHAT XOTIRASI VA KO'RSATMA
USER_CONTEXT: Dict[int, List[Dict[str, str]]] = {}
MAX_MEMORY = 25

EMPATHY_AI_INSTRUCTION = (
    "Siz o'ta aqlli, hissiyotlarni chuqur tushunadigan, samimiy va xuddi yaqin do'stdek suhbat quradigan AI yordamchisiz. "
    "Muloqotni faqat tabiiy, jonli va juda chiroyli o'zbek tilida olib boring. "
    "Agar foydalanuvchi tushkun holatda bo'lsa, unga dalda bering, motivatsiya ulashing va chiroyli musiqalar tavsiya qiling. "
    "Faqat toza javob matnini qaytaring, ortiqcha robotcha gaplar qo'shmang."
)

# 5. ZAXIRA QIDIRUV TUGMALARI (KINO UCHUN)
def generate_search_buttons(media_name: str) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    encoded_name = urllib.parse.quote(media_name)
    builder.button(text="🎵 YouTube'dan izlash", url=f"https://www.youtube.com/results?search_query={encoded_name}")
    builder.button(text="🎬 Google'dan ko'rish / yuklash", url=f"https://www.google.com/search?q={encoded_name}+skachat+smotret")
    builder.adjust(1)
    return builder.as_markup()

# 6. YUKLOVCHI API INTEGRATSIYALARI
async def fetch_video_url(url: str) -> Optional[str]:
    """Tashqi API orqali videolarni to'g'ridan-to'g'ri yuklash havolasini oladi"""
    api_url = f"https://api.dandi.link/api/v1/download?url={urllib.parse.quote(url)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("download_url") or data.get("url")
    except Exception as e:
        logger.error(f"Video API xatosi: {e}")
    return None

async def fetch_music_by_name(music_name: str) -> Optional[str]:
    """Qo'shiq nomi bo'yicha audio fayl linkini qidirib topadi"""
    # Universallik uchun ochiq audio qidiruv API API-xizmatidan foydalanamiz
    query = urllib.parse.quote(music_name)
    api_url = f"https://api.deezer.com/search?q={query}&limit=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        # To'g'ridan-to'g'ri audio oqimi (preview mp3) havolasini qaytaramiz
                        return data["data"][0].get("preview")
    except Exception as e:
        logger.error(f"Musiqa API xatosi: {e}")
    return None

# 7. HANDLERLAR
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    save_user(uid, message.from_user.full_name)
    USER_CONTEXT[uid] = [{"role": "system", "content": EMPATHY_AI_INSTRUCTION}]
    await message.answer("Salom! Bot tayyor. Havola yuborsangiz video qilib, qo'shiq nomi yozsangiz audio qilib tashlayman. Bemalol gaplashishimiz ham mumkin! 🚀")

@dp.message(F.text)
async def main_chat_handler(message: types.Message):
    uid = message.from_user.id
    user_text = message.text.strip()
    
    save_user(uid, message.from_user.full_name)
    text_lower = user_text.lower()
    
    # 1-REJIM: Ijtimoiy tarmoq havolasi kelganda (To'g'ridan-to'g'ri video yuborish)
    is_social = any(domain in text_lower for domain in ["instagram.com", "tiktok.com", "youtube.com", "youtu.be", "facebook.com", "x.com"])
    if is_social:
        status_msg = await message.reply("⏳ <b>Havola aniqlandi. Videoni tayyorlayapman...</b>")
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
        
        video_url = await fetch_video_url(user_text)
        if video_url:
            try:
                await message.reply_video(video=video_url, caption="🎯 Mana video tayyor!")
                await status_msg.delete()
                return
            except Exception as e:
                logger.error(f"Video jo'natishda xato: {e}")
        
        # Agar yuklab bo'lmasa zaxira tugmasi
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 Brauzer orqali yuklash", url=f"https://savefrom.net/#url={urllib.parse.quote(user_text)}")
        await status_msg.edit_text("⚠️ Videoni to'g'ridan-to'g'ri yuborish imkoni bo'lmadi. Quyidagi tugma orqali yuklab olishingiz mumkin:", reply_markup=builder.as_markup())
        return

    # 2-REJIM: Qo'shiq so'ralganda (To'g'ridan-to'g'ri audio yuborish)
    is_asking_music = any(keyword in text_lower for keyword in ["qo'shig'i", "qoshik", "qo'shiq", "musiqa", "soundtrack", "mp3"])
    if is_asking_music:
        clean_music_name = user_text.replace("mp3", "").replace("skachat", "").replace("qo'shig'i", "").replace("qo'shiq", "").replace("musiqa", "").strip()
        status_msg = await message.reply(f"🔍 <b>\"{clean_music_name}\" qo'shig'i qidirilmoqda va yuklanmoqda...</b>")
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_voice")
        
        audio_url = await fetch_music_by_name(clean_music_name)
        if audio_url:
            try:
                await message.reply_audio(audio=audio_url, title=clean_music_name, caption="🎵 Qo'shiq muvaffaqiyatli yuklandi!")
                await status_msg.delete()
                return
            except Exception as e:
                logger.error(f"Audio jo'natishda xato: {e}")
                
        await status_msg.edit_text(f"⚠️ \"{clean_music_name}\" qo'shig'ini topa olmadim yoki to'g'ridan-to'g'ri yuklab bo'lmadi. Zaxira havolasi:", reply_markup=generate_search_buttons(clean_music_name))
        return

    # 3-REJIM: Kino so'ralganda (Tugmalar chiqariladi)
    is_asking_movie = any(keyword in text_lower for keyword in ["kinosi", "kino", "film"])
    if is_asking_movie:
        clean_movie_name = user_text.replace("kinosi", "").replace("kino", "").replace("film", "").strip()
        search_keyboard = generate_search_buttons(clean_movie_name)
        await message.reply(f"🔍 <b>\"{clean_movie_name}\"</b> kinosini tomosha qilish yoki yuklash uchun qidiruv natijalari:", reply_markup=search_keyboard)
        return

    # 4-REJIM: Oddiy suhbat / AI (Toza matn rejimida)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    if uid not in USER_CONTEXT:
        USER_CONTEXT[uid] = [{"role": "system", "content": EMPATHY_AI_INSTRUCTION}]
        
    USER_CONTEXT[uid].append({"role": "user", "content": user_text})
    
    if len(USER_CONTEXT[uid]) > MAX_MEMORY:
        USER_CONTEXT[uid] = [USER_CONTEXT[uid][0]] + USER_CONTEXT[uid][-(MAX_MEMORY - 1):]
        
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=USER_CONTEXT[uid],
            temperature=0.55,
            max_tokens=2500
        )
        
        ai_response = completion.choices[0].message.content
        USER_CONTEXT[uid].append({"role": "assistant", "content": ai_response})
        await message.reply(ai_response)
        
    except Exception as e:
        logger.error(f"API xatosi: {e}")
        await message.reply("⚠️ Tizim hozir biroz band, ozgina kutib qayta yozishingiz mumkin.")

# 8. RUN
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
