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


def get_valid_positions():
    return ['Администратор', 'Официант', 'Повар', 'Бармен']


def insert_user(full_name, position):
    valid_positions = get_valid_positions()
    if position not in valid_positions:
        raise ValueError(f"Недопустимая роль '{position}'. Разрешено: {', '.join(valid_positions)}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO employees (full_name, position) VALUES (?, ?)",
            (full_name, position)
        )
        return cursor.lastrowid


def delete_user_by_id(employee_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))


def get_user_by_id(employee_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, position FROM employees WHERE id = ?", (employee_id,))
        return cursor.fetchone()


def get_all_users():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, position FROM employees ORDER BY id")
        return cursor.fetchall()
