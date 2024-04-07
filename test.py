import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('oi_data.db', check_same_thread=False)
c = conn.cursor()

# Выполнение запроса на выборку всех записей из таблицы oi_records
c.execute('SELECT * FROM oi_records')

# Получение всех результатов запроса
rows = c.fetchall()

# Вывод результатов
for row in rows:
    print(row)

# Закрытие соединения с базой данных
conn.close()
