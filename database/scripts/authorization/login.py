import sqlite3
from pathlib import Path


def _find_db():
    for parent in Path(__file__).resolve().parents:
        if parent.name == "database":
            return parent / "capycafe.db"
    return Path(__file__).resolve().parents / "capycafe.db"


DB_PATH = _find_db()


def get_user_by_id(employee_id):
    """Ищет сотрудника в БД по его уникальному ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, position FROM employees WHERE id = ?", (employee_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_role_permissions(position):
    """Возвращает список доступных прецедентов (действий) на основе роли."""
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
    """Интерфейс авторизации по ID."""
    print("\n=== СИСТЕМА ВХОДА В CAPYCAFE ===")
    user_input = input("Введите ваш ID сотрудника для входа: ").strip()

    if not user_input.isdigit():
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
