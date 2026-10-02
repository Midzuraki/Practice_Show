import sqlite3
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = CURRENT_DIR
while os.path.basename(BASE_DIR) != "practice3" and BASE_DIR != os.path.dirname(BASE_DIR):
    BASE_DIR = os.path.dirname(BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "database", "capycafe.db")


def populate_database():
    print("--- ЗАПУСК ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ ---")

    # Порядок вставки строгий: сначала справочники, затем транзакции
    insert_query = """
    PRAGMA foreign_keys = ON;

    -- 1. Категории
    INSERT INTO categories (id, name) VALUES 
    (1, 'Закуски'), (2, 'Салаты'), (3, 'Супы'), (4, 'Горячие блюда'), (5, 'Десерты'), (6, 'Напитки');

    -- 2. Сотрудники
    INSERT INTO employees (id, full_name, position) VALUES 
    (1, 'Иванов Иван Иванович', 'Официант'),
    (2, 'Петрова Анна Сергеевна', 'Официант'),
    (3, 'Сидоров Алексей Петрович', 'Повар'),
    (4, 'Кузнецов Дмитрий Владимирович', 'Бармен'),
    (5, 'Смирнова Елена Николаевна', 'Администратор');

    -- 3. Статусы заказов
    INSERT INTO order_statuses (id, name) VALUES 
    (1, 'Принят'), (2, 'Готовится'), (3, 'Готов'), (4, 'Выдан'), (5, 'Оплачен'), (6, 'Отменён');

    -- 4. Блюда меню
    INSERT INTO dishes (id, name, description, price, is_available, category_id) VALUES 
    (1, 'Гренки чесночные', 'Ржаные гренки с чесночным соусом', 150.00, 1, 1),
    (2, 'Салат Цезарь', 'Классический салат с курицей', 350.00, 1, 2),
    (3, 'Уха Астраханская', 'Традиционный суп из местной рыбы', 400.00, 1, 3),
    (4, 'Борщ', 'Классический мясной борщ со сметаной', 300.00, 1, 3),
    (5, 'Стейк из судака', 'Судак на гриле с овощами', 550.00, 1, 4),
    (6, 'Котлеты по-киевски', 'С картофельным пюре', 450.00, 1, 4),
    (7, 'Торт Наполеон', 'Домашний слоеный торт', 250.00, 1, 5),
    (8, 'Морс ягодный', 'Собственного приготовления', 100.00, 1, 6),
    (9, 'Кофе Капучино', 'Классический кофейный напиток', 180.00, 0, 6);

    -- 5. Заказы
    INSERT INTO orders (id, order_date, table_number, employee_id, status_id) VALUES 
    (1, '2026-10-01 13:15:00', 3, 1, 5),
    (2, '2026-10-02 12:00:00', 5, 2, 2),
    (3, '2026-10-02 12:30:00', 12, 1, 5);

    -- 6. Позиции заказов (Состав чеков)
    INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES 
    (1, 1, 2, 150.00),
    (1, 3, 1, 400.00),
    (2, 2, 1, 350.00),
    (2, 6, 2, 450.00),
    (3, 5, 1, 550.00),
    (3, 7, 2, 250.00),
    (3, 8, 3, 100.00);
    """

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executescript(insert_query)
        conn.commit()
        print("СТАТУС: Демонстрационные данные успешно записаны в базу.")
    except sqlite3.Error as e:
        print(f"СТАТУС: Ошибка при заполнении таблиц: {e}")
    finally:
        if conn:
            conn.close()
            print("Соединение закрыто.")


if __name__ == "__main__":
    populate_database()
