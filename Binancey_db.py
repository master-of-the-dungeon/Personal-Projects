import asyncio
import aiohttp
from datetime import datetime
import sqlite3
import telebot
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
from telebot import threading
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
    open_interest REAL NOT NULL,
    last_price REAL NOT NULL
)
''')
conn.commit()


api_key = 'sXrs7ucv4aQ8Dbkkaz3NRp1ADV7ld7NKV9cLtkCmPaDDXH6JcrrOQEbhVY9YsWSY'
api_secret = 'QHbwJxEZUq0kmThvdNyIfWuUYXltORJVZBbcb5317BKrDeebw4ojk9V4gUshDntT'
# Инициализация клиента Binance
client = Client(api_key, api_secret)

# Получение всех символов
def get_all_symbols():
    try:
        info = client.futures_exchange_info()
        return [symbol['symbol'] for symbol in info['symbols']]
    except BinanceAPIException as e:
        logging.error(f"Ошибка получения списка символов: {e}")
        return []

all_symbols = get_all_symbols()

# Инициализация телеграм-бота
TELEGRAM_TOKEN = '7066463143:AAE0vEzHOCAYL6SFoENoxHTNWMKwcRg_VxA'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_states = {}
SET_THRESHOLD = 'set_threshold'
SET_INTERVAL = 'set_interval'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    bot.reply_to(message, "Welcome! Use /set_threshold or /set_interval to set your preferences.")

@bot.message_handler(commands=['set_threshold'])
def set_threshold_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = SET_THRESHOLD
    bot.send_message(chat_id, "Please send the new threshold value.")

@bot.message_handler(commands=['set_interval'])
def set_interval_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = SET_INTERVAL
    bot.send_message(chat_id, "Please send the new interval value in minutes.")

@bot.message_handler(func=lambda message: message.chat.id in user_states)
def set_value(message):
    chat_id = message.chat.id
    if user_states[chat_id] == SET_THRESHOLD:
        try:
            threshold = float(message.text)
            bot.send_message(chat_id, f"Threshold has been set to {threshold}%.")
            del user_states[chat_id]
        except ValueError:
            bot.send_message(chat_id, "Invalid value. Please send a numerical value.")
    elif user_states[chat_id] == SET_INTERVAL:
        try:
            interval = int(message.text)
            bot.send_message(chat_id, f"Interval has been set to {interval} minutes.")
            del user_states[chat_id]
        except ValueError:
            bot.send_message(chat_id, "Invalid value. Please send a numerical value.")

async def fetch_open_interest_and_price(session, symbol):
    oi_url = 'https://fapi.binance.com/fapi/v1/openInterest'
    price_url = 'https://api.binance.com/api/v3/ticker/price'
    async with session.get(oi_url, params={'symbol': symbol}) as oi_response, \
         session.get(price_url, params={'symbol': symbol}) as price_response:
        oi_data = await oi_response.json()
        price_data = await price_response.json()
        if oi_response.status == 200 and price_response.status == 200:
            return float(oi_data['openInterest']), float(price_data['price']), datetime.now().isoformat()
        else:
            logging.error(f"Failed to fetch data for {symbol}, HTTP status: {oi_response.status}, {price_response.status}")
            return None, None, None

async def manage_db(symbol, open_interest, last_price, timestamp):
    with conn:
        conn.execute("INSERT INTO oi_records (symbol, timestamp, open_interest, last_price) VALUES (?, ?, ?, ?)", 
                     (symbol, timestamp, open_interest, last_price))
        conn.execute("DELETE FROM oi_records WHERE id IN (SELECT id FROM oi_records WHERE symbol = ? ORDER BY id DESC LIMIT -1 OFFSET 3600)", (symbol,))

async def fetch_and_analyze_oi(symbol):
    async with aiohttp.ClientSession() as session:
        while True:
            current_oi, current_price, current_timestamp = await fetch_open_interest_and_price(session, symbol)
            if current_oi is not None:
                # Действия по анализу и отправке сообщений
                logging.info(f"OI for {symbol}: {current_oi}, price: {current_price}")
            await asyncio.sleep(60)  # Check every minute

async def main():
    tasks = [fetch_and_analyze_oi(symbol) for symbol in all_symbols]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.polling(non_stop=True)).start()
    asyncio.run(main())
