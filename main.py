import os
import logging
import asyncio
import sqlite3
import urllib.parse
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
logger = logging.getLogger("UltimateDynamicBot")

# 2. SOZLAMALAR
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

# 5. LINKLAR VA QIDIRUVLAR UCHUN FUNKSIYALAR
def detect_and_format_link(text: str) -> Optional[types.InlineKeyboardMarkup]:
    """Ijtimoiy tarmoq havolalari aniqlansa, yuklash tugmalarini yasaydi"""
    text_lower = text.lower()
    builder = InlineKeyboardBuilder()
    
    is_social = any(domain in text_lower for domain in ["instagram.com", "tiktok.com", "youtube.com", "youtu.be", "facebook.com", "twitter.com", "x.com"])
    
    if is_social:
        # Xavfsiz va universal yuklash xizmati (SaveFrom / Snaptik muqobili orqali)
        encoded_url = urllib.parse.quote(text)
        download_service = f"https://savefrom.net/#url={encoded_url}"
        
        builder.button(text="📥 Videoni Yuklab Olish", url=download_service)
        builder.adjust(1)
        return builder.as_markup()
    return None

def generate_search_buttons(media_name: str) -> types.InlineKeyboardMarkup:
    """Kino yoki qo'shiq nomi yozilganda qidiruv tugmalarini yasaydi"""
    builder = InlineKeyboardBuilder()
    encoded_name = urllib.parse.quote(media_name)
    
    # YouTube qidiruv havolasi
    builder.button(text="🎵 YouTube'dan izlash/eshitish", url=f"https://www.youtube.com/results?search_query={encoded_name}")
    # Google orqali yuklash / tomosha qilish havolasi
    builder.button(text="🎬 Google'dan yuklash / ko'rish", url=f"https://www.google.com/search?q={encoded_name}+skachat+smotret")
    
    builder.adjust(1)
    return builder.as_markup()

# 6. HANDLERLAR
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    save_user(uid, message.from_user.full_name)
    USER_CONTEXT[uid] = [{"role": "system", "content": EMPATHY_AI_INSTRUCTION}]
    await message.answer("Salom! Botimiz endi yanada kuchli. Bemalol gaplashishingiz, qo'shiq/kino nomlarini yozishingiz yoki ijtimoiy tarmoq havolalarini yuklash uchun tashlashingiz mumkin! 🚀")

@dp.message(F.text)
async def main_chat_handler(message: types.Message):
    uid = message.from_user.id
    user_text = message.text.strip()
    
    save_user(uid, message.from_user.full_name)
    
    # 1-REJIM: Agar matn shunchaki havola (link) bo'lsa
    link_keyboard = detect_and_format_link(user_text)
    if link_keyboard:
        await message.reply("🎯 Havola aniqlandi! Quyidagi tugma orqali mediani tez va oson yuklab olishingiz mumkin:", reply_markup=link_keyboard)
        return

    # AI tahlili orqali qidiruv niyatini aniqlash uchun bot matnini tayyorlaymiz
    text_lower = user_text.lower()
    is_asking_media = any(keyword in text_lower for keyword in ["kinosi", "qo'shig'i", "skachat", "yuklash", "kino nomi", "qoshik nomi", "qo'shiq", "musiqa"]) or (len(user_text.split()) <= 4 and any(w in text_lower for w in ["kino", "kushik", "soundtrack", "film"]))

    # 2-REJIM: Agar foydalanuvchi aniq bir media (kino/qo'shiq) nomini yozgan bo'lsa
    if is_asking_media:
        # Toza nomni ajratib olish (ortiqcha 'skachat' kabi so'zlarni qidiruv sifatli bo'lishi uchun qoldiramiz)
        clean_name = user_text.replace("skachat", "").replace("yuklash", "").strip()
        search_keyboard = generate_search_buttons(clean_name)
        await message.reply(f"🔍 <b>\"{clean_name}\"</b> bo'yicha qidiruv natijalari tayyorlandi. Yuklab olish yoki tomosha qilish uchun quyidagi tugmalardan foydalanishingiz mumkin:", reply_markup=search_keyboard)
        return

    # 3-REJIM: Oddiy suhbat, dardlashish yoki savol-javob (Toza matn rejimida)
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
        await message.reply("⚠️ Hozir biroz yuklama bor, bir necha soniyadan so'ng qayta yozishingiz mumkin.")

# 7. RUN
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
