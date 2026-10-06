import sqlite3
from pathlib import Path


def get_db_path():
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        db_path = parent / "database" / "capycafe.db"
        if db_path.exists():
            return db_path
    raise FileNotFoundError("Не удалось найти database/capycafe.db")


DB_PATH = get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_categories(cursor):
    cursor.execute("SELECT id, name FROM categories ORDER BY id")
    return cursor.fetchall()


def print_categories(categories):
    print("\nДоступные категории: ")
    for category_id, name in categories:
        print(f"  {category_id} - {name}")


def add_dish():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            categories = get_categories(cursor)

            if not categories:
                print("Ошибка: в базе нет категорий.")
                return

            print_categories(categories)

            category_id = int(input("\nID категории: "))
            if category_id not in {row[0] for row in categories}:
                print("Ошибка: такой категории нет.")
                return

            name = input("Название блюда: ").strip()
            description = input("Описание блюда: ").strip()
            price = float(input("Цена (руб.): "))

            if not name:
                print("Ошибка: название не может быть пустым.")
                return
            if price <= 0:
                print("Ошибка: цена должна быть больше нуля.")
                return

            cursor.execute(
                """
                INSERT INTO dishes (name, description, price, is_available, category_id)
                VALUES (?, ?, ?, 1, ?)
                """,
                (name, description, price, category_id),
            )
            print(f"Блюдо '{name}' добавлено. ID: {cursor.lastrowid}")

    except ValueError:
        print("Ошибка: некорректный ввод числовых данных.")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")


def delete_dish():
    try:
        dish_id = int(input("ID блюда для удаления: "))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM dishes WHERE id = ?", (dish_id,))
            dish = cursor.fetchone()

            if not dish:
                print("Ошибка: блюдо с таким ID не найдено.")
                return

            cursor.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
            print(f"Блюдо '{dish[0]}' удалено.")

    except ValueError:
        print("Ошибка: ID должен быть числом.")
    except sqlite3.IntegrityError:
        print("Ошибка: блюдо используется в других записях и не может быть удалено.")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")


def edit_dish():
    try:
        dish_id = int(input("ID блюда для изменения: "))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, description, price, category_id
                FROM dishes
                WHERE id = ?
                """,
                (dish_id,),
            )
            dish = cursor.fetchone()

            if not dish:
                print("Ошибка: блюдо с таким ID не найдено.")
                return

            old_name, old_description, old_price, old_category_id = dish

            print(
                f"\nТекущее блюдо:\n"
                f"Название: {old_name}\n"
                f"Описание: {old_description}\n"
                f"Цена: {old_price}\n"
                f"Категория ID: {old_category_id}"
            )
            print("Оставьте поле пустым, чтобы сохранить текущее значение.")

            name = input(f"Название [{old_name}]: ").strip()
            description = input(f"Описание [{old_description}]: ").strip()
            price_input = input(f"Цена [{old_price}]: ").strip()

            categories = get_categories(cursor)
            print_categories(categories)
            category_input = input(
                f"ID категории [{old_category_id}]: "
            ).strip()

            name = name or old_name
            description = description if description else old_description

            if price_input:
                price = float(price_input)
                if price <= 0:
                    print("Ошибка: цена должна быть больше нуля.")
                    return
            else:
                price = old_price

            if category_input:
                category_id = int(category_input)
                if category_id not in {row[0] for row in categories}:
                    print("Ошибка: такой категории нет.")
                    return
            else:
                category_id = old_category_id

            cursor.execute(
                """
                UPDATE dishes
                SET name = ?, description = ?, price = ?, category_id = ?
                WHERE id = ?
                """,
                (name, description, price, category_id, dish_id),
            )

            print(f"Блюдо с ID {dish_id} изменено.")

    except ValueError:
        print("Ошибка: некорректный ввод числовых данных.")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")


def main():
    actions = {
        "1": add_dish,
        "2": delete_dish,
        "3": edit_dish,
    }

    while True:
        print(
            "\n1. Добавить блюдо\n"
            "2. Удалить блюдо\n"
            "3. Изменить блюдо\n"
            "0. Выход"
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break

        action = actions.get(choice)
        if action:
            action()
        else:
            print("Ошибка: неизвестный пункт меню.")


if __name__ == "__main__":
    main()
