from pybit.unified_trading import HTTP
import time, requests

session = HTTP(testnet=True, api_key="MblPwBPEGa292NpXWJ", api_secret="Pi5esYdz5EIDKYMTKw71cuEPdbvptAVANyQZ")

def get_all_symbols():
    url = "https://api.bybit.com/v2/public/symbols"  
    try:
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()
        if data['ret_code'] == 0:
            
            symbols = [item['name'] for item in data['result']]
            return symbols
        else:
            print(f"Ошибка API: {data['ret_msg']}")
            return []
    except requests.RequestException as e:
        print(f"Ошибка запроса: {e}")
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
            print(f"Данные OI для {symbol} недоступны.")
            return None
    else:
        print(f"Ошибка при получении данных OI для {symbol}: {response.get('retMsg', 'Нет сообщения об ошибке')}")
        return None


def monitor_OI_changes(threshold=5.0):
    symbols = get_all_symbols() 
    
    while True:
        current_time = int(time.time() * 1000)  
        past_time = current_time - 900 * 1000  
        
        for symbol in symbols:
            current_oi = get_open_interest(symbol, timestamp=current_time)
            past_oi = get_open_interest(symbol, timestamp=past_time)
            
            if current_oi is not None and past_oi is not None: 
                change = ((current_oi - past_oi) / past_oi) * 100
                if abs(change) >= threshold:
                    print(f"ВНИМАНИЕ: OI для {symbol} изменился на {change:.2f}% за последние 15 минут.")
            
            time.sleep(1) 


monitor_OI_changes(5.0)  




