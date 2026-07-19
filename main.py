import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from groq import Groq

# Tokenlarni tizim muhitidan olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Mashhur o'zbekcha mem-audio (golos) va qo'shiqlar uchun tayyor linklar (Telegram direct URL yoki ochiq fayllar)
MEM_AUDIOS = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", # Bular namuna, keyinchalik o'zingizning audio linklaringizni qo'yishingiz mumkin
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
]

# Mashhur mem GIFlar uchun linklar
MEM_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExbWxiY21nd3d3ZzVpY3g0ZXN4N3R5NXA0Ynd3ODZwdnl6Y3N5eWJuZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7517S6XFfXjOALew/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z0bXN6ZnNndXN3bXp3OHd3Z3p5NXA0Ynd3ODZwdnl6Y3N5eWJuZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/d1E1msx7Yw5Ne1Fe/giphy.gif"
]

AI_SYSTEM_PROMPT = (
    "Siz o'zbekcha internet memlarini mukammal biladigan, juda aqlli, pichingchi va quvnoq botisiz. "
    "Muloqot uslubingiz sodda, ko'cha tilida va tushunarli bo'lsin, so'zlarni xato yozmang, imlo xatolar qilmang! "
    "Foydalanuvchi bilan 'sen' deb gaplashing. Agar foydalanuvchi qisqa yoz desa qisqa yozing, "
    "ma'lumot so'rasa o'tkir hazillar bilan tushuntiring. Har bir gapni ma'nosini tushunib, to'g'ri o'zbek tilida javob bering."
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Opa-singillar, aka-ukalar! Kim kelganini ko'ringlar! 😎\n\n"
        "Men eng daxshat internet memlarini biladigan aqlli botman. "
        "Menga xohlasang yoz, xohlasang GIF tashla — hammasiga chotki javob qaytaraman. Qani boshladik!"
    )

# 1. Foydalanuvchi GIF (Animation) tashlaganda ishlaydigan qism
@dp.message(F.animation)
async def handle_gif(message: types.Message):
    # GIF kelganda AI unga mos kulgili gap o'ylab topadi
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": "Men hozirgina senga bitta kulgili GIF tashladim. Ushbu GIFga mos bitta daxshat, o'tkir memcha javob yozib ber."}
            ],
            temperature=0.7
        )
        ai_response = completion.choices[0].message.content
        
        # Javob bilan birga bot ham tasodifiy bitta mem GIF qaytaradi
        random_gif = random.choice(MEM_GIFS)
        await message.reply_animation(animation=random_gif, caption=ai_response)
    except Exception as e:
        await message.reply("GIFingga gap yo'q, lekin mening simlarim sal chigallashib qoldi!")

# 2. Oddiy matnli xabarlar kelganda ishlaydigan qism
@dp.message(F.text)
async def handle_ai_chat(message: types.Message):
    user_text = message.text
    
    try:
        # Haroratni (temperature) 0.7 qildik, shunda AI so'zlarni xato yozmaydi, chiroyli va tushunarli gapiradi
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7
        )
        
        ai_response = completion.choices[0].message.content
        
        # Ba'zida (masalan, 30% holatda) bot shunchaki matn emas, ovozli mem (golos) ham qo'shib yuboradi
        if random.random() < 0.3:
            random_audio = random.choice(MEM_AUDIOS)
            await message.reply_audio(audio=random_audio, caption=ai_response)
        else:
            await message.reply(ai_response)
        
    except Exception as e:
        await message.reply("Xatolik bo'ldi. Boshqatdan yozib ko'r-chi, miyam joyiga kelib olsin.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
