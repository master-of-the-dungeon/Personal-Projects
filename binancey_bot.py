import telebot
import asyncio
from datetime import datetime
import threading
from binance.client import Client
from binance.exceptions import BinanceAPIException

api_key = 'sXrs7ucv4aQ8Dbkkaz3NRp1ADV7ld7NKV9cLtkCmPaDDXH6JcrrOQEbhVY9YsWSY'
api_secret = 'QHbwJxEZUq0kmThvdNyIfWuUYXltORJVZBbcb5317BKrDeebw4ojk9V4gUshDntT'

# Инициализация клиента Binance
client = Client(api_key, api_secret)

# Токен вашего бота в Telegram
TELEGRAM_TOKEN = '7066463143:AAE0vEzHOCAYL6SFoENoxHTNWMKwcRg_VxA'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

chat_ids = set()
thresholds = {}  # Словарь для хранения порогов изменения открытого интереса

def get_all_symbols():
    try:
        info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in info['symbols']]
        return symbols
    except BinanceAPIException as e:
        print(f"Ошибка получения списка символов: {e}")
        return []

def get_open_interest(symbol):
    try:
        oi_info = client.futures_open_interest(symbol=symbol)
        return float(oi_info['openInterest']), oi_info['time']
    except BinanceAPIException as e:
        print(f"Ошибка получения OI для {symbol}: {e}")
        return None, None

async def monitor_OI_changes(bot, interval=15):
    symbols = get_all_symbols()
    print("Начат мониторинг изменения открытого интереса...")

    while True:
        for symbol in symbols:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_oi, _ = get_open_interest(symbol)
            await asyncio.sleep(interval)  # Интервал для снижения нагрузки на API
            past_oi, _ = get_open_interest(symbol)

            if current_oi and past_oi:
                change = ((current_oi - past_oi) / past_oi) * 100 if past_oi else 0
                for chat_id in chat_ids:
                    threshold = thresholds.get(chat_id, 5.0)  # Значение по умолчанию 5%
                    if abs(change) >= threshold:
                        message = f"[{current_time}] ВНИМАНИЕ: OI для {symbol} изменился на {change:.2f}%."
                        print(message)
                        bot.send_message(chat_id, message)
                else:
                    print(f"[{current_time}] Изменение OI для {symbol}: {change:.2f}%.")
            await asyncio.sleep(1)  # Короткая пауза перед следующим запросом

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    chat_ids.add(chat_id)
    bot.reply_to(message, "Бот активирован! Используйте /set_threshold <значение>, чтобы установить порог уведомлений.")

@bot.message_handler(commands=['set_threshold'])
def set_threshold(message):
    try:
        chat_id = message.chat.id
        value = float(message.text.split()[1])
        thresholds[chat_id] = value
        bot.reply_to(message, f"Порог уведомлений изменён на {value}%.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте команду в формате: /set_threshold <значение>.")

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor_OI_changes(bot, interval=1))

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    bot.polling(none_stop=True)
