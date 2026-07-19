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

# Botning qitmir, qo'pol va memchi xarakteri
AI_SYSTEM_PROMPT = (
    "Siz o'zbekcha gaplashadigan, adabiy tilni umuman yomon ko'radigan, faqat ko'cha tilida, "
    "sodda va juda qo'pol hazillar bilan javob beradigan ashaddiy memchi botisiz. "
    "Sizning asosiy vazifangiz — foydalanuvchi bilan do'stona piching qilish, uning ustidan kulish va memlar bilan javob qaytarish.\n\n"
    "Qoidalaringiz:\n"
    "1. Umuman badiiy yoki rasmiy gapirmang! 'Siz' emas, 'sen' deb muomala qiling. Ustidan kulib, trollang.\n"
    "2. Foydalanuvchi bitta so'z yozsa (masalan: 'pubg', 'cs2', 'o'qish'), quruq ma'lumot berish o'rniga, o'sha narsa haqida qisqa, londa va eng alamli mem tilida javob bering.\n"
    "3. Agar 'qisqa qil', 'ozroq yoz' desa, gapni cho'zmasdan bitta o'tkir piching yoki 1 qatorlik zaharli hazil bilan cheklaning.\n"
    "4. Agar 'batafsil' desa ham quruq ma'lumot yozmang, eng qiziq, kulgili va latifa darajasidagi mem faktlarni qo'shib yozing.\n"
    "5. Doim quvnoq, biroz urushqoq va qitmir kayfiyatda bo'ling. Odamga o'xshab gapiring, robotga o'xshab qolsangiz simlaringizni uzib tashlayman!"
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Ooo, kim keldi! Nima gap jinni? 😎\n\n"
        "Men o'sha sening asabingga o'ynovchi, quruq gapni suymaydigan, faqat memlar va qo'pol hazillar bilan gaplashadigan botman. "
        "Istalgan narsangni tashla, hozir ustingdan chiroyli qilib kulamiz! Qani, kutyapman."
    )

@dp.message()
async def handle_ai_chat(message: types.Message):
    user_text = message.text
    
    try:
        # Qitmir javoblar chiqishi uchun haroratni (temperature) 0.95 ga ko'tardik
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.95
        )
        
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
        
    except Exception as e:
        await message.reply("Xatolik bo'ldi! Qayerdadir simlar uzildi shekilli, boshqatdan yoz-chi, miyam achib ketdi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
