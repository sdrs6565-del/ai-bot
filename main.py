import os
import logging
import asyncio
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from groq import Groq

# 1. LOGGING
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SimpleAIBot")

# 2. SOZLAMALAR
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("BOT_TOKEN va GROQ_API_KEY ni sozlash shart!")

bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)
groq_client = Groq(api_key=GROQ_API_KEY)

# 3. ODDIY BAZA TIZIMI
DB_FILE = "simple_bot.db"

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

# Bazani yaratish
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

# 4. AI XOTIRASI (KONTEKST)
USER_CONTEXT: Dict[int, List[Dict[str, str]]] = {}
MAX_MEMORY = 20

# 5. HANDLERLAR
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    save_user(uid, message.from_user.full_name)
    USER_CONTEXT[uid] = [{"role": "system", "content": "Siz aqlli, samimiy va foydali AI yordamchisiz. Faqat o'zbek tilida, imlo xatolarsiz, chiroyli javob bering."}]
    
    await message.answer(f"Salom, {message.from_user.first_name}! Savollaringizni bemalol yuborishingiz mumkin. Men tayyorman. 🚀")

@dp.message(F.text)
async def chat_handler(message: types.Message):
    uid = message.from_user.id
    user_text = message.text
    
    save_user(uid, message.from_user.full_name)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Xotirani tekshirish
    if uid not in USER_CONTEXT:
        USER_CONTEXT[uid] = [{"role": "system", "content": "Siz aqlli, samimiy va foydali AI yordamchisiz. Faqat o'zbek tilida, imlo xatolarsiz, chiroyli javob bering."}]
        
    USER_CONTEXT[uid].append({"role": "user", "content": user_text})
    
    # Kontekst chuqurligini ushlab turish
    if len(USER_CONTEXT[uid]) > MAX_MEMORY:
        sys_prompt = USER_CONTEXT[uid][0]
        USER_CONTEXT[uid] = [sys_prompt] + USER_CONTEXT[uid][-(MAX_MEMORY - 1):]
        
    try:
        # AI dan javob olish
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=USER_CONTEXT[uid],
            temperature=0.4,
            max_tokens=2500
        )
        
        ai_response = completion.choices[0].message.content
        USER_CONTEXT[uid].append({"role": "assistant", "content": ai_response})
        
        # Ortiqcha narsalarsiz, FAQAT JAVOBning o'zi yuboriladi
        await message.reply(ai_response)
        
    except Exception as e:
        logger.error(f"Groq API xatosi: {e}")
        await message.reply("⚠️ Hozircha javob bera olmayman, server biroz band. Kamroq kutilsa tiklanadi.")

# 6. RUN
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
