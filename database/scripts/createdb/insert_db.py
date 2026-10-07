import sys
import sqlite3
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

DB_PATH = PROJECT_ROOT / "database" / "capycafe.db"

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

def populate_database():
    insert_query = """
    PRAGMA foreign_keys = ON;

    -- 1. Категории
    INSERT OR IGNORE INTO categories (id, name) VALUES 
    (1, 'Закуски'), (2, 'Salaty'), (3, 'Супы'), (4, 'Горячие блюда'), (5, 'Десерты'), (6, 'Напитки');

    -- 2. Сотрудники (Полный состав для генерации тестовой рабочей среды)
    INSERT OR IGNORE INTO employees (id, full_name, position) VALUES 
    (1, 'Иванов Иван Иванович', 'Официант'),
    (2, 'Петрова Анна Сергеевна', 'Официант'),
    (3, 'Сидоров Алексей Петрович', 'Повар'),
    (4, 'Кузнецов Дмитрий Владимирович', 'Бармен'),
    (5, 'Смирнова Елена Николаевна', 'Администратор');

    -- 3. Статусы заказов
    INSERT OR IGNORE INTO order_statuses (id, name) VALUES 
    (1, 'Принят'), (2, 'Готовится'), (3, 'Готов'), (4, 'Выдан'), (5, 'Оплачен'), (6, 'Отменён');

    -- 4. Блюда меню
    INSERT OR IGNORE INTO dishes (id, name, description, price, is_available, category_id) VALUES 
    (1, 'Гренки чесночные', 'Ржаные гренки с чесночным соусом', 150.00, 1, 1),
    (2, 'Салат Цезарь', 'Классический салат с курицей', 350.00, 1, 2),
    (3, 'Уха Астраханская', 'Традиционный суп из местной рыбы', 400.00, 1, 3),
    (4, 'Борщ', 'Классический мясной борщ со сметаной', 300.00, 1, 3),
    (5, 'Стейк из судака', 'Судак на гриле с овощами', 550.00, 1, 4),
    (6, 'Котлеты по-киевски', 'С картофельным пюре', 450.00, 1, 4),
    (7, 'Торт Наполеон', 'Домашний слоеный торт', 250.00, 1, 5),
    (8, 'Морс ягодный', 'Собственного приготовления', 100.00, 1, 6),
    (9, 'Кофе Капучино', 'Классический кофейный напиток', 180.00, 0, 6);

    -- 5. Заказы (Разные статусы: активные в работе и закрытые для отчетов)
    INSERT OR IGNORE INTO orders (id, order_date, table_number, employee_id, status_id) VALUES 
    (1, '2026-10-01 13:15:00', 3, 1, 5), -- Завершенный (Оплачен)
    (2, '2026-10-07 19:30:00', 5, 2, 2), -- Активный (Готовится)
    (3, '2026-10-07 20:00:00', 12, 1, 1); -- Активный (Принят)

    -- 6. Позиции заказов (Состав чеков)
    INSERT OR IGNORE INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES 
    (1, 1, 2, 150.00),
    (1, 3, 1, 400.00),
    (2, 2, 1, 350.00),
    (2, 6, 2, 450.00),
    (3, 5, 1, 550.00),
    (3, 7, 2, 250.00),
    (3, 8, 3, 100.00);
    """

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(insert_query)
        conn.commit()
        print("Данные успешно записаны в базу.")
    except sqlite3.Error as e:
        print(f"Ошибка при заполнении таблиц: {e}")
    finally:
        if conn:
            conn.close()

def main():
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.executescript(sql_query)
        conn.commit()
        print("УСПЕХ: Все 6 таблиц успешно созданы в базе данных!")

        populate_database()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nСписок созданных таблиц в базе:")
        for t in tables:
            print(f" - {t[0]}")

    except sqlite3.Error as e:
        print(f"\n Текст ошибки:\n{e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
