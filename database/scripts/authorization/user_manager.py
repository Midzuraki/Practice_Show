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


def get_valid_positions():
    return ['Администратор', 'Официант', 'Повар', 'Бармен']


def _check_user_data(full_name, position):
    if not isinstance(full_name, str) or not full_name.strip():
        raise ValueError("ФИО не может быть пустым.")
    valid_positions = get_valid_positions()
    if position not in valid_positions:
        raise ValueError(f"Недопустимая роль '{position}'. Разрешено: {', '.join(valid_positions)}")
    return full_name.strip()


def insert_user(full_name, position):
    full_name = _check_user_data(full_name, position)
    with _db() as conn:
        return conn.execute(
            "INSERT INTO employees (full_name, position) VALUES (?, ?)", (full_name, position)
        ).lastrowid


def update_user(employee_id, full_name, position):
    full_name = _check_user_data(full_name, position)
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE employees SET full_name = ?, position = ? WHERE id = ?", (full_name, position, employee_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("Сотрудник не найден.")


def delete_user_by_id(employee_id):
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone():
            raise ValueError("Сотрудник не найден.")
        if conn.execute("SELECT 1 FROM orders WHERE employee_id = ? LIMIT 1", (employee_id,)).fetchone():
            raise sqlite3.IntegrityError("Сотрудник принимал заказы: его нельзя удалить.")
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))


def get_user_by_id(employee_id):
    with _db() as conn:
        return conn.execute(
            "SELECT id, full_name, position FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()


def get_all_users():
    with _db() as conn:
        return conn.execute("SELECT id, full_name, position FROM employees ORDER BY id").fetchall()
