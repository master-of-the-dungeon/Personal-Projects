import requests

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


symbols = get_all_symbols()
print(symbols)
print('\n')
print(len(symbols))