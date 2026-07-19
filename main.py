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

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Salom! Men aqlli AI botman. Istalgan savolingizni berishingiz mumkin!")

@dp.message()
async def handle_ai_chat(message: types.Message):
    # Foydalanuvchi yozgan matnni olamiz
    user_text = message.text
    
    try:
        # Groq AI modeliga so'rov yuboramiz
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Siz o'zbek tilida so'zlashuvchi aqlli va yordam beruvchi AI bot hisoblanasiz."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7
        )
        # AI javobini foydalanuvchiga qaytaramiz
        ai_response = completion.choices[0].message.content
        await message.reply(ai_response)
    except Exception as e:
        await message.reply("Xatolik yuz berdi, iltimos qaytadan urinib ko'ring.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
