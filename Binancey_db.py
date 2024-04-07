import asyncio
import aiohttp
from datetime import datetime
import sqlite3
import telebot
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация БД
conn = sqlite3.connect('oi_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS oi_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open_interest REAL NOT NULL
)
''')
conn.commit()

api_key = 'sXrs7ucv4aQ8Dbkkaz3NRp1ADV7ld7NKV9cLtkCmPaDDXH6JcrrOQEbhVY9YsWSY'
api_secret = 'QHbwJxEZUq0kmThvdNyIfWuUYXltORJVZBbcb5317BKrDeebw4ojk9V4gUshDntT'
# Инициализация клиента Binance
client = Client(api_key, api_secret)

def get_all_symbols():
    try:
        info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in info['symbols']]
        return symbols
    except BinanceAPIException as e:
        logging.error(f"Ошибка получения списка символов: {e}")
        return []

all_symbols = get_all_symbols()

TELEGRAM_TOKEN = '7066463143:AAE0vEzHOCAYL6SFoENoxHTNWMKwcRg_VxA'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

subscribers = set()
thresholds = {}
intervals = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    thresholds[chat_id] = 5.0  # Значение порога по умолчанию
    intervals[chat_id] = 60    # Интервал по умолчанию в минутах
    bot.reply_to(message, "Вы подписались на уведомления. Используйте /set_threshold и /set_interval для настройки.")

@bot.message_handler(commands=['set_threshold'])
def set_threshold(message):
    try:
        chat_id = message.chat.id
        _, threshold = message.text.split()
        thresholds[chat_id] = float(threshold)
        bot.reply_to(message, f"Порог установлен на {threshold}%.")
    except ValueError:
        bot.reply_to(message, "Используйте: /set_threshold [значение].")

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    try:
        chat_id = message.chat.id
        _, interval = message.text.split()
        intervals[chat_id] = int(interval)
        bot.reply_to(message, f"Интервал установлен на {interval} минут.")
    except ValueError:
        bot.reply_to(message, "Используйте: /set_interval [минуты].")

async def fetch_open_interest(session, symbol):
    url = 'https://fapi.binance.com/fapi/v1/openInterest'
    params = {'symbol': symbol}
    async with session.get(url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            return float(data['openInterest']), datetime.now().isoformat()
        else:
            logging.error(f"Failed to fetch OI for {symbol}, HTTP status: {response.status}")
            return None, None

async def manage_db(symbol, open_interest, timestamp):
    with conn:
        conn.execute("INSERT INTO oi_records (symbol, timestamp, open_interest) VALUES (?, ?, ?)", (symbol, timestamp, open_interest))
        conn.execute("DELETE FROM oi_records WHERE id IN (SELECT id FROM oi_records WHERE symbol = ? ORDER BY id DESC LIMIT -1 OFFSET 3600)", (symbol,))

async def fetch_and_analyze_oi(symbol):
    async with aiohttp.ClientSession() as session:
        previous_oi = None
        previous_timestamp = None
        while True:
            current_oi, current_timestamp = await fetch_open_interest(session, symbol)
            if current_oi is not None and previous_oi is not None:
                change = ((current_oi - previous_oi) / previous_oi) * 100
                for chat_id in subscribers:
                    if abs(change) >= thresholds.get(chat_id, 5.0):
                        bot.send_message(chat_id, f"Significant change in OI for {symbol}: {change:.2f}% from {previous_oi} to {current_oi} at {current_timestamp}")
            previous_oi = current_oi
            previous_timestamp = current_timestamp
            await asyncio.sleep(60)  # Check every minute

async def main():
    tasks = [fetch_and_analyze_oi(symbol) for symbol in all_symbols]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: bot.polling(non_stop=True)).start()
    asyncio.run(main())
