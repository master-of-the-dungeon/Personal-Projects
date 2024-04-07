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
            logger.info("Successfully retrieved symbol list.")
            return symbols
        else:
            logger.error(f"API Error: {data['ret_msg']}")
            return []
    except requests.RequestException as e:
        logger.exception(f"Request Error: {e}")
        return []

def get_open_interest(symbol, category="inverse", interval="5min", startTime=None, endTime=None):
    if startTime and endTime:
        params = {
            "symbol": symbol,
            "category": category,
            "intervalTime": interval,
            "startTime": startTime,
            "endTime": endTime
        }

        response = session.get_open_interest(**params)

        if response and response['retCode'] == 0 and response['result']['list']:
            open_interest_values = [float(item['openInterest']) for item in response['result']['list']]
            logger.info(f"Retrieved OI data for {symbol}: {open_interest_values}")
            return open_interest_values
        else:
            logger.error(f"Failed to retrieve OI data for {symbol}: {response.get('retMsg', 'No error message provided')}")
            return None
    else:
        logger.error("Start time and end time must be provided for the OI data retrieval.")
        return None

def monitor_OI_changes():
    symbols = get_all_symbols()
    if not symbols:
        logger.warning("No symbols available for monitoring.")
        return

    while True:
        current_time = int(time.time() * 1000)
        past_time = current_time - 5 * 60 * 1000  # Five-minute interval in milliseconds

        for symbol in symbols:
            open_interest_values = get_open_interest(symbol, startTime=past_time, endTime=current_time)

            if open_interest_values:
                current_oi = open_interest_values[0]
                past_oi = open_interest_values[-1]
                if past_oi != 0:
                    change = ((current_oi - past_oi) / past_oi) * 100
                    logger.info(f"OI for {symbol} at current: {current_oi}, past: {past_oi}, change: {change:.2f}%")
                    for chat_id in subscribers:
                        user_threshold = thresholds.get(chat_id, 0.1)  # User-defined threshold
                        if abs(change) >= user_threshold:
                            message = f"ALERT: OI for {symbol} changed by {change:.2f}% in the last 5 minutes.\nCurrent OI: {current_oi}\nPrevious OI: {past_oi}"
                            try:
                                bot.send_message(chat_id, message)
                                logger.info(f"Message sent to {chat_id}: {message}")
                            except Exception as e:
                                logger.error(f"Failed to send message to {chat_id}: {str(e)}")
            else:
                logger.warning(f"Insufficient data for OI change calculation for {symbol}.")
            time.sleep(1)  # Moderate the request rate

@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        bot.send_message(chat_id, "You have subscribed to OI change notifications. Use /set_threshold to set a threshold and /set_interval to set the time interval.")
        logger.info(f"New subscriber: {chat_id}")
    else:
        bot.send_message(chat_id, "You are already subscribed.")
        logger.info(f"Re-subscription attempt by {chat_id}")

@bot.message_handler(commands=['set_threshold'])
def set_threshold(message):
    chat_id = message.chat.id
    try:
        value = float(message.text.split()[1])
        thresholds[chat_id] = value
        bot.send_message(chat_id, f"Threshold for notifications changed to {value}%.")
        logger.info(f"User {chat_id} set threshold to {value}%.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Use the command in the format: /set_threshold <value>.")
        logger.warning(f"Incorrect threshold command from user {chat_id}.")

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    chat_id = message.chat.id
    try:
        value = int(message.text.split()[1])
        if value < 1:
            raise ValueError("Interval must be greater than 0")
        intervals[chat_id] = value
        bot.send_message(chat_id, f"Notification interval changed to {value} minutes.")
        logger.info(f"User {chat_id} set interval to {value} minutes.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Use the command in the format: /set_interval <minutes>.")
        logger.warning(f"Incorrect interval command from user {chat_id}.")

def run_bot():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    threading.Thread(target=monitor_OI_changes).start()
    run_bot()
