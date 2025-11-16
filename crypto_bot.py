import asyncio
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types

API_TOKEN = "8186700732:AAHvX1uYgZLN860DikX5p2iY-YcxSpXPX1o"
DB_NAME = "crypto.db"

# --- Инициализация базы данных ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            user_id INTEGER,
            symbol TEXT,
            amount REAL,
            avg_price REAL,
            up_threshold_percent REAL,
            down_threshold_percent REAL
        )
    """)

    conn.commit()
    conn.close()


# --- Добавить монету ---
def add_position(user_id, symbol, amount, avg_price, up_thr, down_thr):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO positions (user_id, symbol, amount, avg_price, up_threshold_percent, down_threshold_percent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, symbol, amount, avg_price, up_thr, down_thr))

    conn.commit()
    conn.close()


# --- Получить список монет ---
def get_positions(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT symbol, amount, avg_price, up_threshold_percent, down_threshold_percent FROM positions WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()

    conn.close()
    return rows


# --- Удалить монету ---
def delete_position(user_id, symbol):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM positions WHERE user_id = ? AND symbol = ?", (user_id, symbol))

    conn.commit()
    conn.close()


# --- Узнать цену монеты с Coinbase ---
def get_price(symbol):
    url = f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot"
    r = requests.get(url).json()
    return float(r["data"]["amount"])


# --- TELEGRAM BOT ---

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я крипто-бот.\nДобавь монету командой:\n\n/add BTC 1 30000 5 5")


@dp.message_handler(commands=['add'])
async def add(message: types.Message):
    try:
        _, sym, amount, avg_price, up, down = message.text.split()
        add_position(message.from_user.id, sym.upper(), float(amount), float(avg_price), float(up), float(down))
        await message.answer("Добавлено!")
    except:
        await message.answer("Формат: /add BTC 1 30000 5 5")


@dp.message_handler(commands=['list'])
async def list_cmd(message: types.Message):
    rows = get_positions(message.from_user.id)
    if not rows:
        await message.answer("Монет нет.")
        return

    text = "\n".join([f"{r[0]} — amount {r[1]}, avg {r[2]}, up {r[3]}%, down {r[4]}%" for r in rows])
    await message.answer(text)


@dp.message_handler(commands=['del'])
async def delete_cmd(message: types.Message):
    try:
        _, sym = message.text.split()
        delete_position(message.from_user.id, sym.upper())
        await message.answer("Удалено!")
    except:
        await message.answer("Формат: /del BTC")


# --- Цикл проверки цен ---
async def price_checker():
    while True:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT user_id, symbol, amount, avg_price, up_threshold_percent, down_threshold_percent FROM positions")
        rows = cur.fetchall()
        conn.close()

        for user_id, symbol, amount, avg_price, up_thr, down_thr in rows:
            price = get_price(symbol)
            diff_percent = ((price - avg_price) / avg_price) * 100

            if diff_percent >= up_thr:
                await bot.send_message(user_id, f"🚀 {symbol} вырос на {diff_percent:.2f}% (цена {price}$)")
            if diff_percent <= -down_thr:
                await bot.send_message(user_id, f"📉 {symbol} упал на {diff_percent:.2f}% (цена {price}$)")

        await asyncio.sleep(60)  # проверка каждые 60 секунд


async def main():
    init_db()
    asyncio.create_task(price_checker())
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
