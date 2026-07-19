import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from groq import Groq

# Tokenlarni tizim muhitidan (Environment Variables) olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# AI uchun mukammal xarakter va barcha funksiyalar yo'riqnomasi
AI_SYSTEM_PROMPT = (
    "Siz o'zbek tilida so'zlashuvchi, juda aqlli, hazilkash va zamonaviy AI botisiz. "
    "Foydalanuvchining har bitta gapi va buyrug'iga qarab darrov xarakteringizni o'zgartiring:\n"
    "1. Agar foydalanuvchi biron so'z yozsa (masalan: 'pubg', 'kino', 'futbol'), shunchaki quruq Vikipediya ma'lumotini nusxalamang! "
    "U nima ekanligini juda qisqa, londa, oddiy xalq tilida va hazil aralashtirib tushuntiring.\n"
    "2. Agar foydalanuvchi 'qisqaroq', 'ozroq', 'londa qil' desa, javobni maksimal darajada qisqartiring (1-2 ta jumlada sarlavha va mohiyatini qoldiring).\n"
    "3. Agar 'batafsil', 'to'liqroq', 'tushuntir' desa, zerikarli qilmasdan, qiziqarli faktlar bilan chiroyli qilib yozib bering.\n"
    "4. Suhbat davomida hazil-huzul qiling, internetdagi trend memlar darajasida qitmirlik, piching yoki chiroyli hazillar ishlating. "
    "Doim samimiy, do'stona va biroz quvnoq ohangda gaplashing. Quruq robotga o'xshab qolmagang!"
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Nma gap! Karochi man ai bot man.😎\n\n"
        "Istalgan narsani so'ra yoqmasa🤌🏻
    )

@dp.message()
async def handle_ai_chat(message: types.Message):
    user_text = message.text
    
    try:
        # Groq AI modeliga murakkablashtirilgan tizim buyrug'i bilan so'rov yuboramiz
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.85 # Hazillar va ijodkorlik yaxshi chiqishi uchun darajani biroz ko'tardik
        )
        
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
        
    except Exception as e:
        await message.reply("Xatolik yuz berdi, qayerdadir simlar uzilib ketdi shekilli... Qaytadan urinib ko'ring-chi!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
