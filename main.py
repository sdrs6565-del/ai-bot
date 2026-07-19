import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq

# Ma'lumotlar
BOT_TOKEN = "8984285444:AAGoOr5bsE7y9B3csiBqag-MxC_ROznxUYs"
GROQ_API_KEY = "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"
ADMIN_ID = 5431692225  # Sizning ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = Groq(api_key=GROQ_API_KEY)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply("Salom! Sizga qanday yordam bera olaman?")
    
    # Foydalanuvchi haqida admin'ga ma'lumot
    info = f"🚀 Bot ishga tushdi!\n👤 Kim: {message.from_user.full_name}\nUsername: @{message.from_user.username}\nID: {message.from_user.id}"
    await bot.send_message(chat_id=ADMIN_ID, text=info)

@dp.message()
async def chat_handler(message: types.Message):
    if message.text:
        # AI dan javob olish
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.text}]
        )
        ai_response = completion.choices[0].message.content
        
        # Foydalanuvchiga yuborish
        await message.reply(ai_response)
        
        # Admin'ga hisobot yuborish
        report = f"👤 Kimdan: {message.from_user.full_name} (@{message.from_user.username})\n💬 Savol: {message.text}\n🤖 AI Javobi: {ai_response}"
        await bot.send_message(chat_id=ADMIN_ID, text=report)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
