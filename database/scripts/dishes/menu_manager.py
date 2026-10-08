import math
import sys
import sqlite3
from contextlib import contextmanager
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

DB_PATH = PROJECT_ROOT / "database" / "capycafe.db"


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


def _clean_name(name, label="Название"):
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{label} не может быть пустым.")
    return name.strip()


def _check_price(price):
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise ValueError("Цена должна быть числом больше нуля.")
    return float(price)



def get_categories():
    with _db() as conn:
        return conn.execute("SELECT id, name FROM categories ORDER BY id").fetchall()


def _ensure_category_name_free(conn, name, exclude_id=None):
    for cid, cname in conn.execute("SELECT id, name FROM categories"):
        if cid != exclude_id and cname.casefold() == name.casefold():
            raise sqlite3.IntegrityError("Категория с таким названием уже существует.")


def add_category(name):
    name = _clean_name(name, "Название категории")
    with _db() as conn:
        _ensure_category_name_free(conn, name)
        return conn.execute("INSERT INTO categories (name) VALUES (?)", (name,)).lastrowid


def rename_category(category_id, name):
    name = _clean_name(name, "Название категории")
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone():
            raise ValueError("Категория не найдена.")
        _ensure_category_name_free(conn, name, exclude_id=category_id)
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))


def delete_category(category_id):
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone():
            raise ValueError("Категория не найдена.")
        if conn.execute("SELECT 1 FROM dishes WHERE category_id = ? LIMIT 1", (category_id,)).fetchone():
            raise sqlite3.IntegrityError("Нельзя удалить категорию, в которой есть блюда.")
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))



def insert_dish(name, description, price, category_id):
    name = _clean_name(name)
    price = _check_price(price)
    with _db() as conn:
        cursor = conn.execute(
            """INSERT INTO dishes (name, description, price, is_available, category_id) 
               VALUES (?, ?, ?, 1, ?)""",
            (name, description, price, category_id)
        )
        return cursor.lastrowid


def get_dish_by_id(dish_id):
    with _db() as conn:
        return conn.execute(
            "SELECT name, description, price, category_id, is_available FROM dishes WHERE id = ?", (dish_id,)
        ).fetchone()


def update_dish(dish_id, name, description, price, category_id, is_available=None):
    name = _clean_name(name)
    price = _check_price(price)
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM dishes WHERE id = ?", (dish_id,)).fetchone():
            raise ValueError("Блюдо не найдено.")
        conn.execute(
            """UPDATE dishes SET name = ?, description = ?, price = ?, category_id = ? 
               WHERE id = ?""",
            (name, description, price, category_id, dish_id)
        )
        if is_available is not None:
            conn.execute("UPDATE dishes SET is_available = ? WHERE id = ?", (1 if is_available else 0, dish_id))


def set_dish_availability(dish_id, is_available):
    with _db() as conn:
        cursor = conn.execute("UPDATE dishes SET is_available = ? WHERE id = ?", (1 if is_available else 0, dish_id))
        if cursor.rowcount == 0:
            raise ValueError("Блюдо не найдено.")


def dish_is_used(dish_id):
    with _db() as conn:
        return conn.execute("SELECT 1 FROM order_items WHERE dish_id = ? LIMIT 1", (dish_id,)).fetchone() is not None


def delete_dish_by_id(dish_id):
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM dishes WHERE id = ?", (dish_id,)).fetchone():
            raise ValueError("Блюдо не найдено.")
        if conn.execute("SELECT 1 FROM order_items WHERE dish_id = ? LIMIT 1", (dish_id,)).fetchone():
            raise sqlite3.IntegrityError("Блюдо использовано в заказах: его нельзя удалить, отметьте как недоступное.")
        conn.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))


def get_dishes(category_id=None, search=None, price_order=None):
    if price_order not in (None, "asc", "desc"):
        raise ValueError("Сортировка должна быть 'asc' или 'desc'.")
    query = """SELECT d.id, d.name, c.name, d.price, d.is_available
               FROM dishes d JOIN categories c ON d.category_id = c.id"""
    params = []
    if category_id is not None:
        query += " WHERE d.category_id = ?"
        params.append(category_id)
    if price_order == "asc":
        query += " ORDER BY d.price ASC, d.name"
    elif price_order == "desc":
        query += " ORDER BY d.price DESC, d.name"
    else:
        query += " ORDER BY d.id"
    with _db() as conn:
        rows = conn.execute(query, params).fetchall()
    if search and search.strip():
        needle = search.strip().casefold()
        rows = [r for r in rows if needle in r[1].casefold()]
    return rows


def search_dishes(part):
    return get_dishes(search=part)


def get_all_tables_data():
    with _db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        db_data = {}
        for table in tables:
            table_name = table[0]
            cursor = conn.execute(f'SELECT * FROM "{table_name}"')
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            db_data[table_name] = (columns, rows)
        return db_data


def get_active_menu():
    with _db() as conn:
        return conn.execute("""
            SELECT d.id, d.name, d.description, d.price, c.name 
            FROM dishes d
            JOIN categories c ON d.category_id = c.id
            WHERE d.is_available = 1
            ORDER BY c.id, d.name
        """).fetchall()
