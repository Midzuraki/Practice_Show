import sqlite3

db_path = r"/database/capycafe.db"

# Чистый SQL-код создания структуры
sql_query = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    position TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    CONSTRAINT chk_dish_price CHECK (price > 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    table_number INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY (status_id) REFERENCES order_statuses(id) ON DELETE RESTRICT,
    CONSTRAINT chk_table_number CHECK (table_number BETWEEN 1 AND 12)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    dish_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_at_order REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE RESTRICT,
    CONSTRAINT chk_item_quantity CHECK (quantity > 0),
    CONSTRAINT chk_item_price CHECK (price_at_order > 0),
    UNIQUE(order_id, dish_id)
);
"""

print("--- Попытка создания таблиц в файле capycafe.db ---")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Запускаем создание структуры
    cursor.executescript(sql_query)
    conn.commit()

    print("УСПЕХ: Все 6 таблиц успешно созданы в базе данных!")

    # Проверяем, видит ли их сама система
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nСписок созданных таблиц в базе:")
    for t in tables:
        print(f" - {t[0]}")

except sqlite3.Error as e:
    print(f"\n❌ ОШИБКА КРИТИЧЕСКАЯ: База отклонила скрипт. Текст ошибки:\n{e}")

finally:
    if conn:
        conn.close()
