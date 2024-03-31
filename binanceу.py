from binance.client import Client
import time

api_key = 'mJyCVC5HS4Kv7dxeBdKr0ac6yfaP3p7bihdSGFiJ1Eb4NLQnQzjFN8vntXYSNPtR'
api_secret = 'iwbEgeUuH27FhvcT2ZQIIRAKN7LvYNrsgeKjzWE3cK8b7oBHiFsdC1q6cjXrtkNX'

# Инициализация клиента Binance
client = Client(api_key, api_secret)

def get_all_symbols():
    # Получаем список всех фьючерсных пар USDT-M
    try:
        info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in info['symbols']]
        return symbols
    except BinanceAPIException as e:
        print(f"Ошибка получения списка символов: {e}")
        return []

def get_open_interest(symbol):
    # Получаем данные об открытом интересе для данного символа
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
            current_oi, _ = get_open_interest(symbol)
            time.sleep(interval)  # Интервал для снижения нагрузки на API
            past_oi, _ = get_open_interest(symbol)
            
            if current_oi and past_oi:
                change = ((current_oi - past_oi) / past_oi) * 100 if past_oi else 0
                if abs(change) >= threshold:
                    print(f"ВНИМАНИЕ: OI для {symbol} изменился на {change:.2f}%.")
                else:
                    print(f"Изменение OI для {symbol}: {change:.2f}%.")
            time.sleep(1)  # Короткая пауза перед следующим запросом

# Вызов функции мониторинга
monitor_OI_changes(interval=15, threshold=5.0)



