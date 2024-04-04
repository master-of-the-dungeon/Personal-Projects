from pybit.unified_trading import HTTP
import telebot
import time
import requests
import threading
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api_key = "MblPwBPEGa292NpXWJ"
api_secret = "Pi5esYdz5EIDKYMTKw71cuEPdbvptAVANyQZ"
TELEGRAM_TOKEN = '7066463143:AAE0vEzHOCAYL6SFoENoxHTNWMKwcRg_VxA'

session = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

subscribers = set()  # Хранение chat_id подписчиков
thresholds = {}  # Словарь для хранения пользовательских порогов изменения открытого интереса
intervals = {}  # Словарь для хранения пользовательских интервалов времени

def get_all_symbols():
    url = "https://api.bybit.com/v2/public/symbols"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['ret_code'] == 0:
            symbols = [item['name'] for item in data['result']]
            logger.info("Успешно получен список символов.")
            return symbols
        else:
            logger.error(f"Ошибка API: {data['ret_msg']}")
            return []
    except requests.RequestException as e:
        logger.exception(f"Ошибка запроса: {e}")
        return []

def get_open_interest(symbol, category="linear", interval="15min", timestamp=None):
    params = {
        "symbol": symbol,
        "category": category,
        "intervalTime": interval,
    }
    if timestamp:
        params["startTime"] = timestamp - 15 * 60 * 1000
        params["endTime"] = timestamp

    response = session.get_open_interest(**params)

    if response and response['retCode'] == 0:
        if response['result']['list']:
            latest_data = response['result']['list'][0]

            return float(latest_data['openInterest'])
        else:
            logger.warning(f"Данные OI для {symbol} недоступны.")
            return None
    else:
        logger.error(f"Ошибка при получении данных OI для {symbol}: {response.get('retMsg', 'Сообщение об ошибке отсутствует')}")
        return None

def monitor_OI_changes():
    while True:
        current_time = int(time.time() * 1000)
        for symbol in get_all_symbols():
            for chat_id in subscribers:
                user_interval = intervals.get(chat_id, 15)  # Значение по умолчанию 15 минут
                past_time = current_time - user_interval * 60 * 1000  # Пересчитываем в миллисекунды

                current_oi = get_open_interest(symbol, timestamp=current_time)
                past_oi = get_open_interest(symbol, timestamp=past_time)

                if current_oi is not None and past_oi is not None:
                    change = ((current_oi - past_oi) / past_oi) * 100
                    user_threshold = thresholds.get(chat_id, 5.0)  # Значение по умолчанию 5%
                    if abs(change) >= user_threshold:
                        message = f"ВНИМАНИЕ: OI для {symbol} изменился на {change:.2f}% за последние {user_interval} минут(ы)."
                        bot.send_message(chat_id, message)
                        logger.info(message)
            time.sleep(60)  # Чтобы избежать слишком частых запросов, лучше установить паузу

@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        bot.send_message(chat_id, "Вы подписались на уведомления об изменениях OI. Используйте /set_threshold для установки порога и /set_interval для установки временного интервала.")
        logger.info(f"Новый подписчик: {chat_id}")
    else:
        bot.send_message(chat_id, "Вы уже подписаны.")
        logger.info(f"Повторная подписка: {chat_id}")

@bot.message_handler(commands=['set_threshold'])
def set_threshold(message):
    chat_id = message.chat.id
    try:
        value = float(message.text.split()[1])
        thresholds[chat_id] = value
        bot.send_message(chat_id, f"Порог уведомлений изменён на {value}%.")
        logger.info(f"Пользователь {chat_id} установил порог на {value}%.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Используйте команду в формате: /set_threshold <значение>.")
        logger.warning(f"Неверная команда установки порога от пользователя {chat_id}.")

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    chat_id = message.chat.id
    try:
        value = int(message.text.split()[1])
        if value < 1:  # Проверяем, чтобы значение было положительным
            raise ValueError("Интервал должен быть больше 0")
        intervals[chat_id] = value
        bot.send_message(chat_id, f"Интервал уведомлений изменён на {value} минут(ы).")
        logger.info(f"Пользователь {chat_id} установил интервал на {value} минут(ы).")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Используйте команду в формате: /set_interval <минуты>.")
        logger.warning(f"Неверная команда установки интервала от пользователя {chat_id}.")

def run_bot():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    # Запуск мониторинга OI в отдельном потоке
    threading.Thread(target=monitor_OI_changes).start()
    # Запуск бота
    run_bot()
