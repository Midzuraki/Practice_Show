import sys
import sqlite3
from contextlib import closing
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


def get_user_by_id(employee_id):
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT id, full_name, position FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()


def get_role_permissions(position):
    permissions = {
        'Администратор': [
            "Просмотреть меню", "Оформить заказ", "Изменить состав заказа",
            "Изменить статус заказа", "Просмотреть заказы",
            "Вести меню и категории", "Вести сотрудников", "Получить отчёты (выручка)"
        ],
        'Официант': [
            "Просмотреть меню", "Оформить заказ", "Изменить состав заказа",
            "Изменить статус заказа", "Просмотреть заказы"
        ],
        'Повар': [
            "Просмотреть меню", "Изменить статус заказа", "Просмотреть заказы"
        ],
        'Бармен': [
            "Просмотреть меню", "Изменить статус заказа", "Просмотреть заказы"
        ]
    }
    return permissions.get(position, [])


def login_ui():
    print("\n=== СИСТЕМА ВХОДА В CAPYCAFE ===")
    user_input = input("Введите ваш ID сотрудника для входа: ").strip()

    if not (user_input.isascii() and user_input.isdecimal()):
        print("Ошибка: ID должен быть числом.")
        return None

    employee_id = int(user_input)
    user = get_user_by_id(employee_id)

    if not user:
        print(f"Ошибка: Сотрудник с ID {employee_id} не найден в базе данных.")
        return None

    uid, full_name, position = user
    print(f"\nУспешный вход!")
    print(f"Пользователь: {full_name}")
    print(f"Роль (ID роли): {position} (ID в базе: {uid})")

    print("\nВаши доступные действия согласно диаграмме прецедентов:")
    actions = get_role_permissions(position)
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action}")

    return user


if __name__ == "__main__":
    login_ui()
