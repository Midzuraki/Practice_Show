import os
import sqlite3
from pathlib import Path

def get_db_path():
    for parent in Path(__file__).resolve().parents:
        if parent.name == "database":
            return parent / "capycafe.db"
    raise FileNotFoundError("Не удалось найти папку 'database' в структуре проекта")

db_path = get_db_path()

def run_test(title, query, expect_error=False):
    print(f"--- {title} ---")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        if expect_error:
            print("СТАТУС: Ошибка (База данных пропустила некорректные данные)")
        else:
            print("СТАТУС: Успешно. Результат выборки:")
            rows = cursor.fetchall()
            if not rows:
                print("   [Данные успешно изменены или результат пуст]")
            else:
                for row in rows:
                    print(f"   {row}")
        conn.commit()
    except sqlite3.Error as e:
        if expect_error:
            print(f"СТАТУС: Успешно (Ограничение СУБД сработало корректно)\n   Детали: {e}")
        else:
            print(f"СТАТУС: Ошибка (Непредвиденное исключение: {e})")
    finally:
        conn.close()
    print("-" * 50)

if __name__ == "__main__":
    if not os.path.exists(db_path):
        print(f"Критическая ошибка: Файл базы данных не найден по пути:\n{db_path}")
        exit(1)

    print("ЗАПУСК ВЕРИФИКАЦИИ И ТЕСТИРОВАНИЯ СТРУКТУРЫ БД CAPYCAFE.DB")
    print("=" * 50)

    run_test(
        "Тест-кейс 1.А: Валидация ограничения chk_dish_price (отрицательная цена)",
        "INSERT INTO dishes (name, price, category_id) VALUES ('Невалидный суп', -50.00, 3);",
        expect_error=True
    )

    run_test(
        "Тест-кейс 1.Б: Валидация ограничения chk_table_number (стол вне лимита 1-12)",
        "INSERT INTO orders (table_number, employee_id, status_id) VALUES (25, 1, 1);",
        expect_error=True
    )

    run_test(
        "Тест-кейс 2: Поиск активных блюд по категории и ключевому слову ('Уха')",
        """
        SELECT d.id, d.name, d.price, c.name 
        FROM dishes d
        JOIN categories c ON d.category_id = c.id
        WHERE d.is_available = 1 AND d.category_id = 3 AND d.name LIKE '%Уха%';
        """,
        expect_error=False
    )

    run_test(
        "Тест-кейс 3: Расчет стоимости активных заказов на основе вложенных позиций",
        """
        SELECT o.id, o.order_date, o.table_number, e.full_name, s.name, COALESCE(SUM(oi.quantity * oi.price_at_order), 0)
        FROM orders o
        JOIN employees e ON o.employee_id = e.id
        JOIN order_statuses s ON o.status_id = s.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        GROUP BY o.id;
        """,
        expect_error=False
    )

    run_test(
        "Тест-кейс 4: Финансовый аналитический отчет (Рейтинг проданных блюд)",
        """
        SELECT d.name, SUM(oi.quantity) AS sold, SUM(oi.quantity * oi.price_at_order) AS revenue
        FROM order_items oi
        JOIN dishes d ON oi.dish_id = d.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status_id = 5
        GROUP BY d.id
        ORDER BY sold DESC;
        """,
        expect_error=False
    )
