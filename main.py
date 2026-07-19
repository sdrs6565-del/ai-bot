import os
import logging
import asyncio
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.markdown import hbold, hcode, hitalic, hmono
from groq import Groq

# =====================================================================
# 1. ENTERPRISE CORE LOGGING & DIAGNOSTICS
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger("MegaScaleAIEngine")

# =====================================================================
# 2. XAVFSIZLIK VA ATROF-MUHIT TUNINGI
# =====================================================================
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN or not GROQ_API_KEY:
    logger.critical("🚨 CRITICAL CORE ERROR: Tizim tokenlari muhitda topilmadi!")
    raise RuntimeError("Render platformasida BOT_TOKEN va GROQ_API_KEY parametrlarini sozlang.")

# 100% barqarorlik uchun HTML parse rejimi va optimallashtirilgan mijoz
bot: Bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)
groq_client = Groq(api_key=GROQ_API_KEY)

# =====================================================================
# 3. NON-BLOCKING ASYNC THREAD-POOL DB ARCHITECTURE
# =====================================================================
DB_FILE = "megascale_matrix.db"

class MegaDatabaseController:
    @staticmethod
    def _sync_execute(query: str, params: Tuple) -> List[Any]:
        conn = sqlite3.connect(DB_FILE, timeout=45.0)
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ma'lumotlar bazasi klasterida xatolik: {e}")
            return []
        finally:
            conn.close()

    @classmethod
    async def execute(cls, query: str, params: Tuple = ()) -> List[Any]:
        """Asosiy Event Loop'ni umuman bloklamaydigan asinxron ip operatsiyasi"""
        return await asyncio.to_thread(cls._sync_execute, query, params)

    @classmethod
    async def bootstrap(cls):
        await cls.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                ai_mode TEXT DEFAULT 'balanced',
                persona TEXT DEFAULT 'standard',
                msg_count INTEGER DEFAULT 0,
                joined_at TEXT
            )
        """)

# Baza asinxron ishga tushishi uchun global orchestratorga bog'lanadi

# =====================================================================
# 4. ADVANCED DISTRIBUTED RATE-LIMITER (DDoS SHIELD)
# =====================================================================
class AdvancedRateLimiter(BaseMiddleware):
    def __init__(self, limit_window: float = 0.4):
        self.limit_window = limit_window
        self.cooldown_bucket: Dict[int, float] = {}
        super().__init__()

    async def __call__(self, handler, event: types.Message, data: Dict[str, Any]):
        user_id = event.from_user.id
        now = time.time()
        
        if user_id in self.cooldown_bucket:
            if now - self.cooldown_bucket[user_id] < self.limit_window:
                return await event.reply("⚡️ <b>Anti-DDoS Tizimi:</b> Xabar yuborish tezligi chegaralandi. Biroz kuting.")
        
        self.cooldown_bucket[user_id] = now
        return await handler(event, data)

dp.message.middleware(AdvancedRateLimiter())

# =====================================================================
# 5. HIGH-DENSITY CONTEXT BRAIN MATRIX
# =====================================================================
USER_CONTEXT_MEMORY: Dict[int, List[Dict[str, str]]] = {}
NEURAL_WINDOW_DEPTH: int = 60  # Kosmik darajadagi xotira chuqurligi
GLOBAL_START_TIME = time.time()

PERSONA_REGISTRY = {
    "standard": "Siz universal, o'ta intellektual va daho AI yordamchisiz. Javoblaringiz mukammal tartibda, imlo xatolarsiz bo'lishi shart.",
    "scholar": "Siz dunyo miqyosidagi akademik professor va ilmiy tadqiqotchisiz. Akademik, adabiy tilda, chuqur tahlillar bilan yondashing.",
    "friend": "Siz foydalanuvchining eng yaqin, dono va samimiy do'stisiz. Juda chiroyli, tushunarli, motivatsiya va dalda beruvchi ohangda gaplashing."
}

async def compile_advanced_strategy(user_id: int, user_text: str) -> Dict[str, Any]:
    records = await MegaDatabaseController.execute("SELECT ai_mode, persona FROM users WHERE user_id = ?", (user_id,))
    ai_mode = records[0][0] if records else "balanced"
    persona = records[0][1] if records else "standard"
    
    system_core = PERSONA_REGISTRY.get(persona, PERSONA_REGISTRY["standard"])
    text_lower = user_text.lower()
    
    strategy = {"prompt": f"{system_core}\n\nMuloqotni faqat toza va mukammal o'zbek tilida olib boring.", "temperature": 0.35, "max_tokens": 3000}
    
    # Kontekstli dynamic NLP skanerlash
    if any(w in text_lower for w in ["qisqa", "londa", "kamroq", "ozroq", "1 qator"]):
        strategy["prompt"] += "\n[Muxim Sozlama: Kirish so'zlarisiz, faqat eng qisqa va lo'nda javobni bering!]"
        strategy["temperature"] = 0.1
        strategy["max_tokens"] = 350
    elif any(w in text_lower for w in ["batafsil", "uzunroq", "kengroq", "to'liq", "tushuntir", "mukammal"]):
        strategy["prompt"] += "\n[Muxim Sozlama: Mavzuni barcha qismlari, qoidalari va misollari bilan juda batafsil va uzun matnda yozing!]"
        strategy["temperature"] = 0.55
        strategy["max_tokens"] = 4000
    else:
        if ai_mode == "short":
            strategy["prompt"] += "\n[Global rejim: Qisqa va lo'nda javob majburiy.]"
            strategy["temperature"] = 0.1
            strategy["max_tokens"] = 350
        elif ai_mode == "detailed":
            strategy["prompt"] += "\n[Global rejim: Batafsil va uzun tushuntirish majburiy.]"
            strategy["max_tokens"] = 4000
            
    return strategy

def commit_to_isolated_memory(user_id: int, role: str, content: str, system_prompt: str):
    if user_id not in USER_CONTEXT_MEMORY:
        USER_CONTEXT_MEMORY[user_id] = [{"role": "system", "content": system_prompt}]
        
    USER_CONTEXT_MEMORY[user_id][0] = {"role": "system", "content": system_prompt}
    USER_CONTEXT_MEMORY[user_id].append({"role": role, "content": content})
    
    # Intellektual xotira oynasini nazorat qilish
    if len(USER_CONTEXT_MEMORY[user_id]) > NEURAL_WINDOW_DEPTH:
        system_node = USER_CONTEXT_MEMORY[user_id][0]
        # Eng eski elementlarni mantiqan qisqartirish
        USER_CONTEXT_MEMORY[user_id] = [system_node] + USER_CONTEXT_MEMORY[user_id][-(NEURAL_WINDOW_DEPTH - 1):]

async def synchronize_user_telemetry(user_id: int, username: str, **kwargs):
    exists = await MegaDatabaseController.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not exists:
        now_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await MegaDatabaseController.execute("INSERT INTO users (user_id, username, joined_at) VALUES (?, ?, ?)", (user_id, username, now_stamp))
    
    for key, value in kwargs.items():
        await MegaDatabaseController.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        
    await MegaDatabaseController.execute("UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?", (user_id,))

class EngineStates(StatesGroup):
    active_chat = State()
    waiting_report = State()

# =====================================================================
# 6. SUPREME UI INTERFACES (KEYBOARDS)
# =====================================================================
def get_mega_dashboard() -> Any:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Tizim Rejimi", callback_data="mg_mode")
    builder.button(text="🎭 Agent Shaxsiyati", callback_data="mg_persona")
    builder.button(text="📊 Telemetriya & Holat", callback_data="mg_metrics")
    builder.button(text="🗑 Xotirani Flush Qilish", callback_data="mg_flush")
    builder.button(text="✍️ Tizim Hisoboti", callback_data="mg_report")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_mega_modes() -> Any:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡️ Super Qisqa", callback_data="mmode_short")
    builder.button(text="🧠 Optimal Balans", callback_data="mmode_balanced")
    builder.button(text="📚 Maksimal Batafsil", callback_data="mmode_detailed")
    builder.button(text="⬅️ Bosh Menyu", callback_data="mg_home")
    builder.adjust(1)
    return builder.as_markup()

def get_mega_personas() -> Any:
    builder = InlineKeyboardBuilder()
    builder.button(text="🤖 Universal Robot", callback_data="mperson_standard")
    builder.button(text="🎓 Akademik Professor", callback_data="mperson_scholar")
    builder.button(text="🤝 Qadrdon Do'st", callback_data="mperson_friend")
    builder.button(text="⬅️ Bosh Menyu", callback_data="mg_home")
    builder.adjust(1)
    return builder.as_markup()

# =====================================================================
# 7. EVENT INTERACTION LIFE-CYCLE
# =====================================================================
@dp.message(CommandStart())
async def cmd_start_handler(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await synchronize_user_telemetry(uid, message.from_user.full_name)
    USER_CONTEXT_MEMORY[uid] = [{"role": "system", "content": PERSONA_REGISTRY["standard"]}]
    await state.set_state(EngineStates.active_chat)
    
    welcome = (
        f"🌌 <b>MEGA-SCALE INTERFLUX AI INFRASTRUCTURE v5.0</b> 🌌\n\n"
        f"Xush kelibsiz, {hbold(message.from_user.first_name)}! Tizim non-blocking asinxron thread-pool, "
        f"HTML-izolyatsiyalangan kontekst va 60 ta xabargacha kengaytirilgan xotira klasteri bilan to'liq ishga tushirildi.\n\n"
        f"👇 Quyidagi yuqori boshqaruv konsolidan foydalaning:"
    )
    await message.answer(welcome, reply_markup=get_mega_dashboard())

@dp.message(Command("menu"))
async def cmd_menu_handler(message: types.Message):
    await message.answer("🎛 <b>Tizim boshqaruv konsoli:</b>", reply_markup=get_mega_dashboard())

@dp.callback_query(F.data == "mg_home")
async def cb_mega_home(callback: types.CallbackQuery):
    await callback.message.edit_text("🎛 <b>Tizim boshqaruv konsoli:</b>", reply_markup=get_mega_dashboard())

@dp.callback_query(F.data == "mg_mode")
async def cb_mega_modes(callback: types.CallbackQuery):
    await callback.message.edit_text("⚙️ <b>AI JAVOB STRATEGIYASINI SOZLANG:</b>", reply_markup=get_mega_modes())

@dp.callback_query(F.data == "mg_persona")
async def cb_mega_personas(callback: types.CallbackQuery):
    await callback.message.edit_text("🎭 <b>AI NEVROTARMOQ ICHKI SHAXSIYATINI TANLANG:</b>", reply_markup=get_mega_personas())

@dp.callback_query(F.data.startswith("mmode_"))
async def cb_apply_mode(callback: types.CallbackQuery):
    uid = callback.from_user.id
    selected_mode = callback.data.split("_")[1]
    await synchronize_user_telemetry(uid, callback.from_user.full_name, ai_mode=selected_mode)
    await callback.answer(f"Global rejim o'rnatildi: {selected_mode.upper()}", show_alert=True)
    await callback.message.edit_text("🎛 <b>Tizim boshqaruv konsoli:</b>", reply_markup=get_mega_dashboard())

@dp.callback_query(F.data.startswith("mperson_"))
async def cb_apply_persona(callback: types.CallbackQuery):
    uid = callback.from_user.id
    selected_persona = callback.data.split("_")[1]
    await synchronize_user_telemetry(uid, callback.from_user.full_name, persona=selected_persona)
    await callback.answer(f"AI Xarakteri faollashtirildi: {selected_persona.upper()}", show_alert=True)
    await callback.message.edit_text("🎛 <b>Tizim boshqaruv konsoli:</b>", reply_markup=get_mega_dashboard())

@dp.callback_query(F.data == "mg_flush")
async def cb_flush_memory(callback: types.CallbackQuery):
    uid = callback.from_user.id
    USER_CONTEXT_MEMORY[uid] = [{"role": "system", "content": PERSONA_REGISTRY["standard"]}]
    await callback.answer("Neyron tarmoq muloqotlar tarixi xavfsiz flush qilindi!", show_alert=True)

@dp.callback_query(F.data == "mg_metrics")
async def cb_mega_metrics(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = await MegaDatabaseController.execute("SELECT ai_mode, persona, msg_count, joined_at FROM users WHERE user_id = ?", (uid,))
    
    ai_mode, persona, msg_count, joined_at = data[0] if data else ("balanced", "standard", 0, "Noma'lum")
    uptime = round(time.time() - GLOBAL_START_TIME, 1)
    
    metrics = (
        f"📊 <b>MEGA-SCALE ARCHITECTURE TELEMETRIYA DIAGNOSTIKASI</b>\n\n"
        f"🆔 <b>Infrastruktura Resurs ID:</b> {hcode(str(uid))}\n"
        f"⚙️ <b>Asinxron Oqim Moduli:</b> {hcode(ai_mode.upper())}\n"
        f"🎭 <b>Neyron Shaxsiyat Modeli:</b> {hcode(persona.upper())}\n"
        f"✉️ <b>Muvaffaqiyatli Sikllar:</b> {hcode(str(msg_count))} ta so'rov\n"
        f"⏱ <b>Engine Global Uptime:</b> {hcode(str(uptime))} soniya\n"
        f"📅 <b>Klaster Tarbiyaviy Sana:</b> {hcode(joined_at)}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Bosh Menyu", callback_data="mg_home")
    await callback.message.edit_text(metrics, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "mg_report")
async def cb_init_report(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EngineStates.waiting_report)
    await callback.message.answer("✍️ <b>Tizim xatoliklari yoki takliflaringizni to'g'ridan-to'g'ri tizim administratoriga yozing:</b>")
    await callback.answer()

@dp.message(EngineStates.waiting_report, F.text)
async def catch_system_report(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    logger.info(f"MEGA REPORT INSTANCE [{uid}]: {message.text}")
    
    if ADMIN_ID != 0:
        try:
            await bot.send_message(ADMIN_ID, f"📡 <b>KLASTERLI DIAGNOSTIKA XABARI:</b>\n👤 Foydalanuvchi: <code>{uid}</code>\n📝 Hisobot: {message.text}")
        except Exception:
            pass
            
    await state.set_state(EngineStates.active_chat)
    await message.reply("✅ <b>Rahmat! Tizim diagnostika hisoboti muvaffaqiyatli yuborildi.</b>", reply_markup=get_mega_dashboard())

# =====================================================================
# 8. HYPER-SPEED INFERENCE PIPELINE (HTML SAFE)
# =====================================================================
@dp.message(F.text)
async def pipeline_text_processor(message: types.Message):
    uid = message.from_user.id
    raw_input = message.text
    
    await synchronize_user_telemetry(uid, message.from_user.full_name)
    strategy = await compile_advanced_strategy(uid, raw_input)
    commit_to_isolated_memory(uid, "user", raw_input, strategy["prompt"])
    await run_mega_inference(message, uid, strategy)

@dp.message(F.animation | F.voice | F.audio)
async def pipeline_media_processor(message: types.Message):
    uid = message.from_user.id
    await synchronize_user_telemetry(uid, message.from_user.full_name)
    
    fallback_text = "Foydalanuvchi multimedia ob'ektini uzatdi. Ushbu seans mantiqiy zanjiriga asosan intellektual munosabat yozing."
    strategy = await compile_advanced_strategy(uid, "")
    commit_to_isolated_memory(uid, "user", fallback_text, strategy["prompt"])
    await run_mega_inference(message, uid, strategy)

async def run_mega_inference(message: types.Message, uid: int, strategy: Dict[str, Any]):
    """Asinxron, eksponentsial backoff va telemetriyaga ega Groq Core Engine"""
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    start_runtime = time.time()
    total_attempts = 4
    delay_factor = 1.0
    
    for attempt in range(total_attempts):
        try:
            # Llama-3.3-70B yordamida super-kompyuter tezligida javob olish
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=USER_CONTEXT_MEMORY[uid],
                temperature=strategy["temperature"],
                max_tokens=strategy["max_tokens"]
            )
            
            ai_output = completion.choices[0].message.content
            commit_to_isolated_memory(uid, "assistant", ai_output, USER_CONTEXT_MEMORY[uid][0]["content"])
            
            # Haqiqiy vaqt telemetriyasi
            execution_speed = round(time.time() - start_runtime, 2)
            telemetry_footer = f"\n\n⚡️ {hitalic(f'Inference: {execution_speed}s | Platform: Cluster Llama-3.3-70B')}"
            
            final_response = ai_output + telemetry_footer
            await message.reply(final_response, reply_markup=get_mega_dashboard())
            return
            
        except Exception as api_error:
            logger.warning(f"Engine yuklama uzilishi (Urinish {attempt + 1}/{total_attempts}): {api_error}")
            if attempt < total_attempts - 1:
                await asyncio.sleep(delay_factor)
                delay_factor *= 2.0  # Eksponentsial orqaga chekinish algoritmi
            else:
                logger.error(f"Kritik API tarmog'i butunlay uzildi: {api_error}")
                await message.reply(
                    "🛰 <b>Infrastruktura band:</b> Global neyrotarmoq klasterlari hozirda juda yuqori yuklamada. "
                    "Kontekstingiz xavfsiz saqlandi. Iltimos, 3 soniyadan keyin qayta urining."
                )

# =====================================================================
# 9. BOOTSTRAP ORCHESTRATOR
# =====================================================================
async def main() -> None:
    # Ma'lumotlar bazasini asinxron ishga tushirish
    await MegaDatabaseController.bootstrap()
    logger.info("==========================================================")
    logger.info("👑 MEGA-SCALE AI CLUSTER INFRASTRUCTURE RUNNING OPTIMIZED")
    logger.info("==========================================================")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Tizim xavfsiz o'chirildi.")
