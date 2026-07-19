import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from groq import Groq

# Tokenlarni tizim muhitidan olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# AI uchun mukammal va aqlli yo'riqnoma (Imlo xatolar taqiqlanadi)
AI_SYSTEM_PROMPT = (
    "Siz o'zbek tilida so'zlashuvchi, internet trendlarini va haqiqiy memlarni mukammal biladigan juda aqlli AI botisiz. "
    "Muloqot uslubingiz juda aniq, savodli va to'g'ri o'zbek tilida bo'lishi shart! Hech qanday imlo xatolariga, tushunarsiz so'zlarga yo'l qo'yilmaydi. "
    "Mantiqsiz va sifatsiz ('yemagan') hazillar qilmang. Agar foydalanuvchi qisqa yoz desa, maksimal darajada qisqa va londa javob bering. "
    "Agar batafsil so'rasa, adabiy va tushunarli tilda chiroyli qilib tushuntiring. Foydalanuvchi bilan samimiy, do'stona va biroz quvnoq ohangda suhbatlashing."
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Men o'sha siz kutgan mukammal, aqlli va har qanday vaziyatni tushunadigan AI botman. 🧠✨\n\n"
        "Menga matn yozishingiz, GIF yuborishingiz yoki ovozli xabar (golos) yuborishingiz mumkin. "
        "Hammasini tahlil qilib, sizga eng to'g'ri va eng chiroyli javobni qaytaraman. Qani, boshladik!"
    )

# 1. Foydalanuvchi GIF (Animation) yuborganida ishlaydigan qism
@dp.message(F.animation)
async def handle_gif(message: types.Message):
    try:
        # AI foydalanuvchi GIF yuborganini bilib, unga mos aqlli munosabat bildiradi
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": "Men hozirgina senga bitta kulgili yoki qiziqarli GIF yubordim. Ushbu vaziyatga mos keladigan, o'rinli va juda aqlli o'zbekcha javob yozib ber."}
            ],
            temperature=0.6
        )
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
    except Exception as e:
        await message.reply("Ajoyib GIF! Lekin tizimda biroz uzilish bo'lgani sababli hozir sharhlab bera olmayman. Birozdan keyin urinib ko'ring.")

# 2. Foydalanuvchi Ovozli xabar (Voice/Golos) yuborganida ishlaydigan qism
@dp.message(F.voice | F.audio)
async def handle_audio_or_voice(message: types.Message):
    try:
        # AI foydalanuvchi ovozli xabar yuborganini tushunib javob qaytaradi
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": "Men hozirgina senga ovozli xabar (golos) yubordim. Ovozli xabar yuborganimga mos ravishda samimiy, tushunarli va chiroyli javob qaytar."}
            ],
            temperature=0.6
        )
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
    except Exception as e:
        await message.reply("Ovozli xabaringiz qabul qilindi! Hozircha matnli xabarlar orqali gaplashib turamiz, chunki simlarimiz biroz qizib ketdi.")

# 3. Oddiy matnli xabarlar kelganda ishlaydigan qism
@dp.message(F.text)
async def handle_text_chat(message: types.Message):
    user_text = message.text
    
    try:
        # Temperature darajasini 0.6 qildik, shunda bot gaplarni to'g'ri va mantiqli tuzadi
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6
        )
        
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
        
    except Exception as e:
        await message.reply("Kechirasiz, xatolik yuz berdi. Iltimos, fikringizni qaytadan yozib ko'ring.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
