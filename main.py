import os
import logging
import asyncio
import sqlite3
import urllib.parse
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from groq import Groq

# 1. LOGGING
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SuperPremiumBot")

# 2. SOZLAMALAR
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
ADMIN_USERNAME = "xript12"  # Sizning nikingiz (mualliflik huquqi va adminlik nazorati)

if not BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("BOT_TOKEN va GROQ_API_KEY ni sozlash shart!")

bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)
groq_client = Groq(api_key=GROQ_API_KEY)

# 3. MA'LUMOTLAR BAZASI
DB_FILE = "premium_bot.db"

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
        full_name TEXT,
        msg_count INTEGER DEFAULT 0,
        joined_at TEXT
    )
""")

def save_user(user_id: int, username: str, full_name: str):
    exists = execute_db("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    clean_username = f"@{username}" if username else "Mavjud emas"
    if not exists:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db("INSERT INTO users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)", 
                   (user_id, clean_username, full_name, now))
    else:
        execute_db("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (clean_username, full_name, user_id))
    execute_db("UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?", (user_id,))

# 4. CHAT XOTIRASI VA KO'RSATMA
USER_CONTEXT: Dict[int, List[Dict[str, str]]] = {}
MAX_MEMORY = 25

EMPATHY_AI_INSTRUCTION = (
    "Siz o'ta aqlli, hissiyotlarni chuqur tushunadigan, samimiy va xuddi yaqin do'stdek suhbat quradigan AI yordamchisiz. "
    "Muloqotni faqat tabiiy, jonli va juda chiroyli o'zbek tilida olib boring. "
    "Faqat toza javob matnini qaytaring, ortiqcha robotcha gaplar yoki tizim metrikalarini qo'shmang."
)

# 5. YUKLOVCHI VA KINO TUGMALARI
def generate_movie_keyboards(movie_name: str) -> types.InlineKeyboardMarkup:
    """Uzmovi va Asilmedia platformalaridan to'g'ridan-to'g'ri qidiruv tugmalari"""
    builder = InlineKeyboardBuilder()
    encoded_name = urllib.parse.quote(movie_name)
    
    # Saytlarning ichki qidiruv zanjiriga moslashtirilgan havolalar
    builder.button(text="🎬 Uzmovi'dan tomosha qilish", url=f"https://uzmovi.com/search?q={encoded_name}")
    builder.button(text="🍿 Asilmedia'dan tomosha qilish", url=f"https://asilmedia.org/index.php?do=search&subaction=search&story={encoded_name}")
    builder.button(text="🎵 YouTube'dan qidirish", url=f"https://www.youtube.com/results?search_query={encoded_name}")
    
    builder.adjust(1)
    return builder.as_markup()

async def fetch_direct_media(url: str) -> Optional[str]:
    """KuyNavo va SongFast kabi ishlovchi premium yuklovchi oqim API tarmog'i"""
    api_url = f"https://api.dandi.link/api/v1/download?url={urllib.parse.quote(url)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=35) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("download_url") or data.get("url")
    except Exception as e:
        logger.error(f"Media yuklashda xatolik: {e}")
    return None

async def fetch_music_by_name(music_name: str) -> Optional[str]:
    """Musiqa nomidan to'g'ridan-to'g'ri audio oqimini oladi"""
    query = urllib.parse.quote(music_name)
    api_url = f"https://api.deezer.com/search?q={query}&limit=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0].get("preview")
    except Exception as e:
        logger.error(f"Musiqa qidiruv xatosi: {e}")
    return None

# 6. HANDLERLAR
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    save_user(uid, message.from_user.username, message.from_user.full_name)
    USER_CONTEXT[uid] = [{"role": "system", "content": EMPATHY_AI_INSTRUCTION}]
    await message.answer("<b>Salom! Botimiz premium imkoniyatlar bilan yangilandi.</b> ✨\n\n"
                         "🔹 Havolalarni tashlasangiz, xuddi KuyNavo kabi to'g'ridan-to'g'ri fayl qilib yuklaydi.\n"
                         "🔹 Kino nomlarini yozsangiz, Uzmovi va Asilmedia havolalari bilan topadi.\n"
                         "🔹 Qo'shiq nomini yozsangiz, audio fayl qilib beradi.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Faqat @xript12 uchun ishlaydigan maxfiy ma'lumotlar tizimi"""
    current_username = message.from_user.username
    if current_username and current_username.lower() == ADMIN_USERNAME.lower():
        users_list = execute_db("SELECT user_id, username, full_name, msg_count, joined_at FROM users")
        
        if not users_list:
            await message.answer("📊 Bazada hozircha foydalanuvchilar mavjud emas.")
            return
            
        report = f"📊 <b>Bot foydalanuvchilari haqida to'liq hisobot:</b>\n\n"
        report += f"Total foydalanuvchilar: {len(users_list)} ta\n"
        report += "----------------------------------------\n"
        
        for user in users_list:
            report += (f"👤 <b>Ism:</b> {user[2]}\n"
                       f"🌐 <b>Nik:</b> {user[1]}\n"
                       f"🆔 <b>ID:</b> <code>{user[0]}</code>\n"
                       f"✉️ <b>Xabarlar soni:</b> {user[3]} ta\n"
                       f"📅 <b>Qo'shilgan vaqti:</b> {user[4]}\n"
                       f"----------------------------------------\n")
            
        # Agar matn juda uzun bo'lib ketsa, Telegram limitidan oshmasligi uchun bo'lib yuboramiz
        if len(report) > 4096:
            for x in range(0, len(report), 4096):
                await message.answer(report[x:x+4096])
        else:
            await message.answer(report)
    else:
        await message.answer("⚠️ Ushbu buyruq faqat bot egasi (@xript12) uchun ochiq!")

@dp.message(F.text)
async def main_chat_handler(message: types.Message):
    uid = message.from_user.id
    user_text = message.text.strip()
    
    save_user(uid, message.from_user.username, message.from_user.full_name)
    text_lower = user_text.lower()
    
    # 1-REJIM: Ijtimoiy tarmoq havolasi kelganda (KuyNavo va SongFast kabi yuklash)
    is_social = any(domain in text_lower for domain in ["instagram.com", "tiktok.com", "youtube.com", "youtu.be", "facebook.com", "x.com"])
    if is_social:
        status_msg = await message.reply("⚡ <b>Havola tekshirilmoqda... Mediani tayyorlayapman...</b>")
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
        
        media_file = await fetch_direct_media(user_text)
        if media_file:
            try:
                await message.reply_video(video=media_file, caption="🎯 KuyNavo tizimi orqali yuklandi!")
                await status_msg.delete()
                return
            except Exception as e:
                logger.error(f"Fayl yuborishda xato: {e}")
                
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 Brauzer orqali yuklash", url=f"https://savefrom.net/#url={urllib.parse.quote(user_text)}")
        await status_msg.edit_text("⚠️ Mediani to'g'ridan-to'g'ri yuborish imkoni bo'lmadi. Tugma orqali yuklab oling:", reply_markup=builder.as_markup())
        return

    # 2-REJIM: Qo'shiq so'ralganda (To'g'ridan-to'g'ri audio yuborish)
    is_asking_music = any(keyword in text_lower for keyword in ["qo'shig'i", "qoshik", "qo'shiq", "musiqa", "soundtrack", "mp3"])
    if is_asking_music:
        clean_music_name = user_text.replace("mp3", "").replace("skachat", "").replace("qo'shig'i", "").replace("qo'shiq", "").replace("musiqa", "").strip()
        status_msg = await message.reply(f"📥 <b>\"{clean_music_name}\" qo'shig'i yuklanmoqda...</b>")
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_voice")
        
        audio_url = await fetch_music_by_name(clean_music_name)
        if audio_url:
            try:
                await message.reply_audio(audio=audio_url, title=clean_music_name, caption="🎵 SongFast tizimi orqali yuklandi!")
                await status_msg.delete()
                return
            except Exception as e:
                logger.error(f"Audio jo'natishda xato: {e}")
                
        await status_msg.edit_text(f"⚠️ Qo'shiqni topa olmadim, lekin qidiruv havolalarini tayyorladim:", reply_markup=generate_movie_keyboards(clean_music_name))
        return

    # 3-REJIM: Kino so'ralganda (Uzmovi va Asilmedia tugmalari)
    is_asking_movie = any(keyword in text_lower for keyword in ["kinosi", "kino", "film"])
    if is_asking_movie:
        clean_movie_name = user_text.replace("kinosi", "").replace("kino", "").replace("film", "").strip()
        search_keyboard = generate_movie_keyboards(clean_movie_name)
        await message.reply(f"🔍 <b>\"{clean_movie_name}\"</b> kinosi Uzmovi va Asilmedia platformalaridan qidirildi. Tomosha qilish uchun tugmalarni bosing:", reply_markup=search_keyboard)
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
        await message.reply("⚠️ Hozir tarmoq biroz band, bir necha soniyadan so'ng qayta urinib ko'ring.")

# 7. RUN
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
