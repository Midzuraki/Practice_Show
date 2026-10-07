import sqlite3
from pathlib import Path

def _find_db():
    for parent in Path(__file__).resolve().parents:
        if parent.name == "database":
            return parent / "capycafe.db"
    return Path(__file__).resolve().parents[2] / "capycafe.db"

DB_PATH = _find_db()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_categories():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY id")
        return cursor.fetchall()


def insert_dish(name, description, price, category_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO dishes (name, description, price, is_available, category_id) 
               VALUES (?, ?, ?, 1, ?)""",
            (name, description, price, category_id)
        )
        return cursor.lastrowid


def get_dish_by_id(dish_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, description, price, category_id FROM dishes WHERE id = ?", (dish_id,))
        return cursor.fetchone()


def update_dish(dish_id, name, description, price, category_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE dishes SET name = ?, description = ?, price = ?, category_id = ? 
               WHERE id = ?""",
            (name, description, price, category_id, dish_id)
        )


def delete_dish_by_id(dish_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))


def get_all_tables_data():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = cursor.fetchall()

        db_data = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f'SELECT * FROM "{table_name}"')
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            db_data[table_name] = (columns, rows)
        return db_data

def get_active_menu():
    with get_connection() as conn:
        return conn.execute("""
            SELECT d.id, d.name, d.description, d.price, c.name 
            FROM dishes d
            JOIN categories c ON d.category_id = c.id
            WHERE d.is_available = 1
            ORDER BY c.id, d.name
        """).fetchall()

