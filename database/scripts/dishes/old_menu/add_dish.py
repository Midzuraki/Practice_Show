import os
import sqlite3
from pathlib import Path

def get_db_path():
    for parent in Path(__file__).resolve().parents:
        if parent.name == "database":
            return parent / "capycafe.db"
    raise FileNotFoundError("Не удалось найти папку 'database' в структуре проекта")

db_path = get_db_path()


def add_new_dish():
    print("--- ДОБАВЛЕНИЕ НОВОГО БЛЮДА В МЕНЮ ---")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Вывод существующих категорий
        cursor.execute("SELECT id, name FROM categories;")
        categories = cursor.fetchall()

        print("\nДоступные категории: ")
        for cat in categories:
            print(f"  ID: {cat[0]} - {cat[1]}")

        category_id = int(input("\nВведите ID категории: "))
        name = input("Введите название блюда: ").strip()
        description = input("Введите описание блюда: ").strip()
        price = float(input("Введите цену блюда (руб.): "))

        if price <= 0:
            print("Ошибка: Цена должна быть больше нуля.")
            return

        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
            INSERT INTO dishes (name, description, price, is_available, category_id)
            VALUES (?, ?, ?, 1, ?);
        """, (name, description, price, category_id))

        conn.commit()
        print(f"\nУспешно: Блюдо '{name}' добавлено в меню с ID {cursor.lastrowid}")

    except ValueError:
        print("Ошибка: Некорректный ввод числовых данных.")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    add_new_dish()