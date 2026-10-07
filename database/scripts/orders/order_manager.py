import sqlite3
from pathlib import Path


def _find_db():
    for parent in Path(__file__).resolve().parents:
        if parent.name == "database":
            return parent / "capycafe.db"
    return Path(__file__).resolve().parents / "capycafe.db"


DB_PATH = _find_db()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_order(table_number, employee_id, items):
    if not items:
        raise ValueError("Нельзя создать заказ без позиций (блюд).")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. По умолчанию при создании заказа ставим статус 'Принят' (id = 1)
        cursor.execute(
            """INSERT INTO orders (table_number, employee_id, status_id) 
               VALUES (?, ?, 1)""",
            (table_number, employee_id)
        )
        order_id = cursor.lastrowid

        # 2. Переносим позиции блюд в состав чека с фиксацией текущей цены
        for dish_id, quantity in items:
            # Получаем актуальную цену блюда из меню
            cursor.execute("SELECT price, is_available FROM dishes WHERE id = ?", (dish_id,))
            dish = cursor.fetchone()

            if not dish:
                raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} не найдено в меню.")

            price_at_order, is_available = dish

            if not is_available:
                raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} сейчас недоступно для заказа.")

            cursor.execute(
                """INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) 
                   VALUES (?, ?, ?, ?)""",
                (order_id, dish_id, quantity, price_at_order)
            )

        return order_id


def delete_order_by_id(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))


def get_order_info(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT o.id, o.order_date, o.table_number, e.full_name, s.name 
               FROM orders o
               JOIN employees e ON o.employee_id = e.id
               JOIN order_statuses s ON o.status_id = s.id
               WHERE o.id = ?""",
            (order_id,)
        )
        return cursor.fetchone()


def get_order_items_details(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT d.name, oi.quantity, oi.price_at_order, (oi.quantity * oi.price_at_order) as total
               FROM order_items oi
               JOIN dishes d ON oi.dish_id = d.id
               WHERE oi.order_id = ?""",
            (order_id,)
        )
        return cursor.fetchall()

def get_active_orders():
    with get_connection() as conn:
        return conn.execute("""
            SELECT o.id, o.order_date, o.table_number, e.full_name, s.name 
            FROM orders o
            JOIN employees e ON o.employee_id = e.id
            JOIN order_statuses s ON o.status_id = s.id
            WHERE o.status_id NOT IN (5, 6)
            ORDER BY o.id DESC
        """).fetchall()


def get_statuses():
    with get_connection() as conn:
        return conn.execute("SELECT id, name FROM order_statuses ORDER BY id").fetchall()

def update_order_status(order_id, status_id):
    with get_connection() as conn:
        conn.execute("UPDATE orders SET status_id = ? WHERE id = ?", (status_id, order_id))
