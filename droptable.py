import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('oi_data.db', check_same_thread=False)
c = conn.cursor()

# Выполнение запроса на выборку всех записей из таблицы oi_records
c.execute('drop table oi_records')
conn.close()