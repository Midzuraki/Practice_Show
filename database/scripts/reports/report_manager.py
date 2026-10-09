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
