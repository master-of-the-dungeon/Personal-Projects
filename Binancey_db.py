import asyncio
import aiohttp
from datetime import datetime
import sqlite3
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
    open_interest REAL NOT NULL,
    last_price REAL NOT NULL
)
''')
conn.commit()

async def fetch_open_interest_and_price(session, symbol):
    """Асинхронно получает открытый интерес и последнюю цену для данного символа."""
    url_oi = 'https://fapi.binance.com/fapi/v1/openInterest'
    url_price = 'https://fapi.binance.com/fapi/v1/ticker/price'
    
    # Получение открытого интереса
    async with session.get(url_oi, params={'symbol': symbol}) as response_oi:
        if response_oi.status == 200:
            data_oi = await response_oi.json()
            oi = float(data_oi['openInterest']) if 'openInterest' in data_oi else None
        else:
            logging.error(f"Failed to fetch OI for {symbol}, HTTP status: {response_oi.status}")
            oi = None

    # Получение последней цены
    async with session.get(url_price, params={'symbol': symbol}) as response_price:
        if response_price.status == 200:
            data_price = await response_price.json()
            price = float(data_price['price']) if 'price' in data_price else None
        else:
            logging.error(f"Failed to fetch price for {symbol}, HTTP status: {response_price.status}")
            price = None

    return oi, price, datetime.now().isoformat()

async def manage_db(symbol, open_interest, last_price, timestamp):
    """Управляет записями в базе данных."""
    with conn:
        conn.execute("INSERT INTO oi_records (symbol, timestamp, open_interest, last_price) VALUES (?, ?, ?, ?)",
                     (symbol, timestamp, open_interest, last_price))
        conn.execute("DELETE FROM oi_records WHERE id IN (SELECT id FROM oi_records WHERE symbol = ? ORDER BY id DESC LIMIT -1 OFFSET 3600)", (symbol,))
        logging.info(f"Database updated for {symbol}: OI={open_interest}, Last Price={last_price}, Timestamp={timestamp}")

async def periodic_oi_update(symbols):
    """Периодическое обновление OI и цены для списка символов."""
    async with aiohttp.ClientSession() as session:
        while True:
            for symbol in symbols:
                oi, price, timestamp = await fetch_open_interest_and_price(session, symbol)
                if oi is not None and price is not None:
                    await manage_db(symbol, oi, price, timestamp)
            await asyncio.sleep(1)  # Ожидание 1 секунду перед следующим циклом запросов

async def main():
    symbols = ['BTCUSDT', 'ETHUSDT']  # Указать список интересующих символов
    await periodic_oi_update(symbols)

if __name__ == "__main__":
    asyncio.run(main())
