import sys
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

DB_PATH = PROJECT_ROOT / "database" / "capycafe.db"

STATUS_ACCEPTED, STATUS_COOKING, STATUS_READY, STATUS_SERVED, STATUS_PAID, STATUS_CANCELLED = 1, 2, 3, 4, 5, 6
FINAL_STATUSES = (STATUS_PAID, STATUS_CANCELLED)
MIN_TABLE, MAX_TABLE = 1, 12

# Таблица 2: какие целевые статусы может выставлять роль
ROLE_TARGET_STATUSES = {
    'Повар': {STATUS_COOKING, STATUS_READY},
    'Бармен': {STATUS_COOKING, STATUS_READY},
    'Официант': {STATUS_SERVED, STATUS_PAID, STATUS_CANCELLED},
    'Администратор': {STATUS_ACCEPTED, STATUS_COOKING, STATUS_READY, STATUS_SERVED, STATUS_PAID, STATUS_CANCELLED},
}

ORDER_CREATOR_POSITIONS = ('Официант', 'Администратор')


# Таблица 4: допустимые переходы между статусами (ФТ-14, ФТ-15)
ALLOWED_TRANSITIONS = {
    STATUS_ACCEPTED: {STATUS_COOKING, STATUS_CANCELLED},
    STATUS_COOKING: {STATUS_READY, STATUS_CANCELLED},
    STATUS_READY: {STATUS_SERVED},
    STATUS_SERVED: {STATUS_PAID},
    STATUS_PAID: set(),
    STATUS_CANCELLED: set(),
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_date(text):
    """Переводит дату ДД.ММ.ГГГГ в формат ГГГГ-ММ-ДД."""
    if not isinstance(text, str):
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ.")
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y").date().isoformat()
    except ValueError:
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ.")


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Количество должно быть целым числом больше нуля.")


def _validate_table(table_number):
    if isinstance(table_number, bool) or not isinstance(table_number, int) or not (MIN_TABLE <= table_number <= MAX_TABLE):
        raise ValueError(f"Номер столика должен быть целым числом от {MIN_TABLE} до {MAX_TABLE}.")


def _get_status_id(conn, order_id):
    row = conn.execute("SELECT status_id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        raise ValueError("Заказ не найден.")
    return row[0]


def _ensure_editable(conn, order_id):
    if _get_status_id(conn, order_id) in FINAL_STATUSES:
        raise ValueError("Заказ оплачен или отменён: состав изменять нельзя.")


def create_order(table_number, employee_id, items):
    if not items:
        raise ValueError("Нельзя создать заказ без позиций (блюд).")
    _validate_table(table_number)

    merged = {}
    for dish_id, quantity in items:
        _validate_quantity(quantity)
        merged[dish_id] = merged.get(dish_id, 0) + quantity

    with _db() as conn:
        employee = conn.execute("SELECT position FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if not employee:
            raise ValueError("Сотрудник не найден.")
        if employee[0] not in ORDER_CREATOR_POSITIONS:
            raise ValueError("Оформлять заказы могут только официант и администратор.")
        cursor = conn.execute(
            "INSERT INTO orders (table_number, employee_id, status_id) VALUES (?, ?, ?)",
            (table_number, employee_id, STATUS_ACCEPTED)
        )
        order_id = cursor.lastrowid

        for dish_id, quantity in merged.items():
            dish = conn.execute("SELECT price, is_available FROM dishes WHERE id = ?", (dish_id,)).fetchone()
            if not dish:
                raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} не найдено в меню.")
            price_at_order, is_available = dish
            if not is_available:
                raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} сейчас недоступно для заказа.")
            conn.execute(
                "INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (?, ?, ?, ?)",
                (order_id, dish_id, quantity, price_at_order)
            )
        return order_id


def add_order_item(order_id, dish_id, quantity):
    _validate_quantity(quantity)
    with _db() as conn:
        _ensure_editable(conn, order_id)
        dish = conn.execute("SELECT price, is_available FROM dishes WHERE id = ?", (dish_id,)).fetchone()
        if not dish:
            raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} не найдено в меню.")
        if not dish[1]:
            raise sqlite3.IntegrityError(f"Блюдо с ID {dish_id} сейчас недоступно для заказа.")
        existing = conn.execute(
            "SELECT id FROM order_items WHERE order_id = ? AND dish_id = ?", (order_id, dish_id)
        ).fetchone()
        if existing:
            conn.execute("UPDATE order_items SET quantity = quantity + ? WHERE id = ?", (quantity, existing[0]))
        else:
            conn.execute(
                "INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (?, ?, ?, ?)",
                (order_id, dish_id, quantity, dish[0])
            )


def update_item_quantity(order_id, dish_id, quantity):
    _validate_quantity(quantity)
    with _db() as conn:
        _ensure_editable(conn, order_id)
        cursor = conn.execute(
            "UPDATE order_items SET quantity = ? WHERE order_id = ? AND dish_id = ?", (quantity, order_id, dish_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("Позиция не найдена в заказе.")


def remove_order_item(order_id, dish_id):
    with _db() as conn:
        _ensure_editable(conn, order_id)
        cursor = conn.execute("DELETE FROM order_items WHERE order_id = ? AND dish_id = ?", (order_id, dish_id))
        if cursor.rowcount == 0:
            raise ValueError("Позиция не найдена в заказе.")


def get_order_total(order_id):
    with _db() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(quantity * price_at_order), 0) FROM order_items WHERE order_id = ?", (order_id,)
        ).fetchone()[0]
        return round(total, 2)


def delete_order_by_id(order_id):
    """Заказ целиком не удаляется, вместо этого его отменяют (таблица 9)."""
    raise ValueError("Заказ целиком не удаляется: отмените его (допустимо в статусах «Принят» и «Готовится»).")


def get_order_info(order_id):
    with _db() as conn:
        return conn.execute(
            """SELECT o.id, o.order_date, o.table_number, e.full_name, s.name 
               FROM orders o
               JOIN employees e ON o.employee_id = e.id
               JOIN order_statuses s ON o.status_id = s.id
               WHERE o.id = ?""",
            (order_id,)
        ).fetchone()


def get_order_items_details(order_id):
    with _db() as conn:
        return conn.execute(
            """SELECT d.name, oi.quantity, oi.price_at_order, (oi.quantity * oi.price_at_order) as total
               FROM order_items oi
               JOIN dishes d ON oi.dish_id = d.id
               WHERE oi.order_id = ?
               ORDER BY oi.id""",
            (order_id,)
        ).fetchall()


def get_active_orders():
    with _db() as conn:
        return conn.execute("""
            SELECT o.id, o.order_date, o.table_number, e.full_name, s.name,
                   COALESCE((SELECT SUM(oi.quantity * oi.price_at_order)
                             FROM order_items oi WHERE oi.order_id = o.id), 0) AS total
            FROM orders o
            JOIN employees e ON o.employee_id = e.id
            JOIN order_statuses s ON o.status_id = s.id
            WHERE o.status_id NOT IN (5, 6)
            ORDER BY o.id DESC
        """).fetchall()


def get_orders(status_id=None, date_from=None, date_to=None, newest_first=True):
    iso_from = parse_date(date_from) if date_from else None
    iso_to = parse_date(date_to) if date_to else None
    if iso_from and iso_to and iso_from > iso_to:
        raise ValueError("Начальная дата не может быть позже конечной.")

    query = """SELECT o.id, o.order_date, o.table_number, e.full_name, s.name,
                      COALESCE((SELECT SUM(oi.quantity * oi.price_at_order) FROM order_items oi WHERE oi.order_id = o.id), 0)
               FROM orders o
               JOIN employees e ON o.employee_id = e.id
               JOIN order_statuses s ON o.status_id = s.id"""
    conditions, params = [], []
    if status_id is not None:
        conditions.append("o.status_id = ?")
        params.append(status_id)
    if iso_from:
        conditions.append("date(o.order_date) >= ?")
        params.append(iso_from)
    if iso_to:
        conditions.append("date(o.order_date) <= ?")
        params.append(iso_to)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY o.order_date DESC, o.id DESC" if newest_first else " ORDER BY o.order_date ASC, o.id ASC"
    with _db() as conn:
        return conn.execute(query, params).fetchall()


def get_statuses():
    with _db() as conn:
        return conn.execute("SELECT id, name FROM order_statuses ORDER BY id").fetchall()


def update_order_status(order_id, status_id, role=None):
    if role is not None and role not in ROLE_TARGET_STATUSES:
        raise ValueError(f"Неизвестная роль: {role}.")
    with _db() as conn:
        current = _get_status_id(conn, order_id)
        if status_id not in ALLOWED_TRANSITIONS:
            raise ValueError("Неизвестный статус заказа.")
        if status_id not in ALLOWED_TRANSITIONS[current]:
            raise ValueError("Недопустимый переход статуса заказа.")
        if role is not None and status_id not in ROLE_TARGET_STATUSES[role]:
            raise ValueError(f"Роль «{role}» не может устанавливать этот статус.")
        conn.execute("UPDATE orders SET status_id = ? WHERE id = ?", (status_id, order_id))


def cancel_order(order_id, role=None):
    update_order_status(order_id, STATUS_CANCELLED, role)
