import sys
import sqlite3
from contextlib import contextmanager
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.scripts.orders.order_manager import parse_date, STATUS_PAID

DB_PATH = PROJECT_ROOT / "database" / "capycafe.db"


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_dish_rating():
    with _db() as conn:
        return conn.execute(
            """SELECT d.name, SUM(oi.quantity) AS sold, SUM(oi.quantity * oi.price_at_order) AS revenue
               FROM order_items oi
               JOIN dishes d ON oi.dish_id = d.id
               JOIN orders o ON oi.order_id = o.id
               WHERE o.status_id = ?
               GROUP BY d.id
               ORDER BY sold DESC, d.name""",
            (STATUS_PAID,)
        ).fetchall()



def get_employee_efficiency(date_from=None, date_to=None):
    """Возвращает статистику по официантам на основе оплаченных заказов.

    Количество обслуженных столов считается по числу оплаченных заказов,
    а выручка — по сохранённым в заказе ценам на момент оформления.
    """
    iso_from = parse_date(date_from) if date_from else None
    iso_to = parse_date(date_to) if date_to else None
    if iso_from and iso_to and iso_from > iso_to:
        raise ValueError("Начальная дата не может быть позже конечной.")

    date_conditions = []
    params = [STATUS_PAID]
    if iso_from:
        date_conditions.append("date(o.order_date) >= ?")
        params.append(iso_from)
    if iso_to:
        date_conditions.append("date(o.order_date) <= ?")
        params.append(iso_to)

    join_conditions = ["o.employee_id = e.id"]
    join_conditions.extend(date_conditions)
    order_join = " AND ".join(join_conditions)

    with _db() as conn:
        rows = conn.execute(
            f"""SELECT e.full_name,
                       COUNT(DISTINCT CASE WHEN o.status_id = ? THEN o.id END) AS served_tables,
                       COALESCE(SUM(CASE WHEN o.status_id = ? THEN oi.quantity * oi.price_at_order ELSE 0 END), 0) AS revenue
                FROM employees e
                LEFT JOIN orders o ON {order_join}
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE e.position = 'Официант'
                GROUP BY e.id, e.full_name
                ORDER BY revenue DESC, served_tables DESC, e.full_name""",
            [STATUS_PAID, *params[1:], STATUS_PAID]
        ).fetchall()
        return [(name, count, round(total, 2)) for name, count, total in rows]


def get_cancelled_orders():
    """Возвращает отменённые заказы с их потенциальной стоимостью."""
    from database.scripts.orders.order_manager import STATUS_CANCELLED

    with _db() as conn:
        rows = conn.execute(
            """SELECT o.id, o.order_date, o.table_number, e.full_name,
                      COALESCE(SUM(oi.quantity * oi.price_at_order), 0) AS total
               FROM orders o
               JOIN employees e ON e.id = o.employee_id
               LEFT JOIN order_items oi ON oi.order_id = o.id
               WHERE o.status_id = ?
               GROUP BY o.id, o.order_date, o.table_number, e.full_name
               ORDER BY o.order_date DESC, o.id DESC""",
            (STATUS_CANCELLED,)
        ).fetchall()
        return [(oid, date, table, employee, round(total, 2))
                for oid, date, table, employee, total in rows]

def get_revenue(date_from, date_to=None):
    iso_from = parse_date(date_from)
    iso_to = parse_date(date_to) if date_to else iso_from
    if iso_from > iso_to:
        raise ValueError("Начальная дата не может быть позже конечной.")
    with _db() as conn:
        count, total = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(t.total), 0)
               FROM orders o
               LEFT JOIN (SELECT order_id, SUM(quantity * price_at_order) AS total
                          FROM order_items GROUP BY order_id) t ON t.order_id = o.id
               WHERE o.status_id = ? AND date(o.order_date) BETWEEN ? AND ?""",
            (STATUS_PAID, iso_from, iso_to)
        ).fetchone()
        return count, round(total, 2)
