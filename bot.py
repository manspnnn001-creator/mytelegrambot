import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "8293017756:AAHhgb-Hk22Ot_RyoWgvFR7h9ddnqPoIWGA"
ADMIN_ID = 8173614173  # <-- сюда өз Telegram ID-ңды жаз

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("eco.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    photo_id TEXT,
    status TEXT DEFAULT 'pending'
)
""")
conn.commit()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )
    conn.commit()
    await message.answer("🌍 EcoLife ботына қош келдің!\nФото жіберіп балл жинай бер!")


@dp.message_handler(commands=['profile'])
async def profile(message: types.Message):
    cursor.execute(
        "SELECT points FROM users WHERE telegram_id=?",
        (message.from_user.id,)
    )
    result = cursor.fetchone()
    points = result[0] if result else 0

    await message.answer(f"🌿 Сенің баллың: {points}")


@dp.message_handler(content_types=['photo'])
async def photo_handler(message: types.Message):
    photo_id = message.photo[-1].file_id

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id=?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()
    if not user:
        return

    user_id = user[0]

    cursor.execute(
        "INSERT INTO submissions (user_id, photo_id) VALUES (?, ?)",
        (user_id, photo_id)
    )
    conn.commit()

    submission_id = cursor.lastrowid

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Қабылдау", callback_data=f"approve_{submission_id}"),
        InlineKeyboardButton("❌ Бас тарту", callback_data=f"reject_{submission_id}")
    )

    await bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=f"Жаңа фото!\nUser ID: {message.from_user.id}",
        reply_markup=keyboard
    )

    await message.answer("📸 Фото админге жіберілді!")


@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    submission_id = callback.data.split("_")[1]

    cursor.execute(
        "SELECT user_id FROM submissions WHERE id=?",
        (submission_id,)
    )
    user_id = cursor.fetchone()[0]

    cursor.execute(
        "UPDATE users SET points = points + 1 WHERE id=?",
        (user_id,)
    )

    cursor.execute(
        "UPDATE submissions SET status='approved' WHERE id=?",
        (submission_id,)
    )
    conn.commit()

    cursor.execute(
        "SELECT telegram_id, points FROM users WHERE id=?",
        (user_id,)
    )
    user = cursor.fetchone()
    telegram_id, points = user

    await bot.send_message(telegram_id, f"✅ Фото қабылданды! +1 балл\nЖалпы балл: {points}")

    if points == 20:
        await bot.send_message(telegram_id, "🎉 20 балл жинадың! Сыйлығың бар!")

    await callback.answer("Қабылданды!")


@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    submission_id = callback.data.split("_")[1]

    cursor.execute(
        "SELECT user_id FROM submissions WHERE id=?",
        (submission_id,)
    )
    user_id = cursor.fetchone()[0]

    cursor.execute(
        "SELECT telegram_id FROM users WHERE id=?",
        (user_id,)
    )
    telegram_id = cursor.fetchone()[0]

    cursor.execute(
        "UPDATE submissions SET status='rejected' WHERE id=?",
        (submission_id,)
    )
    conn.commit()

    await bot.send_message(telegram_id, "❌ Фото қабылданбады.")
    await callback.answer("Бас тартылды!")


if __name__ == "__main__":
    executor.start_polling(dp)
