from datetime import datetime
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

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
        print(f"Ошибка получения списка символов: {e}")
        return []

def get_open_interest(symbol):
    try:
        oi_info = client.futures_open_interest(symbol=symbol)
        return float(oi_info['openInterest']), oi_info['time']
    except BinanceAPIException as e:
        print(f"Ошибка получения OI для {symbol}: {e}")
        return None, None

def monitor_OI_changes(interval=15, threshold=5.0):
    symbols = get_all_symbols()
    print("Начат мониторинг изменения открытого интереса...")

    while True:
        for symbol in symbols:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_oi, _ = get_open_interest(symbol)
            time.sleep(interval)  # Интервал для снижения нагрузки на API
            past_oi, _ = get_open_interest(symbol)

            if current_oi and past_oi:
                change = ((current_oi - past_oi) / past_oi) * 100 if past_oi else 0
                if abs(change) >= threshold:
                    print(f"[{current_time}] ВНИМАНИЕ: OI для {symbol} изменился на {change:.2f}%.")
                else:
                    print(f"[{current_time}] Изменение OI для {symbol}: {change:.2f}%.")
            time.sleep(1)  # Короткая пауза перед следующим запросом

monitor_OI_changes(interval=1, threshold=5.0)
