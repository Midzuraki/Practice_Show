import sys
import sqlite3
import subprocess
from pathlib import Path

# Правильный корень проекта (поднимаемся из папки main/ на уровень выше)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "database" / "scripts" / "dishes"))

import menu_manager


# --- Вспомогательные функции для сокращения кода UI ---
def ask_input(prompt, default=None, is_num=False, is_float=False):
    val = input(prompt).strip()
    if not val and default is not None:
        return default
    try:
        return float(val) if is_float else (int(val) if is_num else val)
    except ValueError:
        return None


def run_safe_ui(func):

    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (ValueError, TypeError):
            print("Ошибка: Некорректный ввод числовых данных.")
        except sqlite3.IntegrityError:
            print("Ошибка: Запись используется в других таблицах и защищена от удаления/изменения.")
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")

    return wrapper


def show_categories_ui():
    categories = menu_manager.get_categories()
    if not categories:
        print("Ошибка: в базе нет категорий.")
        return set()
    print("\nДоступные категории: " + "".join(f"\n  {cid} - {name}" for cid, name in categories))
    return {row for row in categories}


@run_safe_ui
def add_dish_ui():
    valid_cats = show_categories_ui()
    if not valid_cats: return

    category_id = ask_input("\nID категории: ", is_num=True)
    if category_id not in valid_cats: return print("Ошибка: такой категории нет.")

    name = ask_input("Название блюда: ")
    description = ask_input("Описание блюда: ")
    price = ask_input("Цена (руб.): ", is_float=True)

    if not name or not price or price <= 0:
        return print("Ошибка: некорректное название или цена.")

    last_id = menu_manager.insert_dish(name, description, price, category_id)
    print(f"Блюдо '{name}' добавлено. ID: {last_id}")


@run_safe_ui
def delete_dish_ui():
    dish_id = ask_input("ID блюда для удаления: ", is_num=True)
    dish = menu_manager.get_dish_by_id(dish_id)
    if not dish: return print("Ошибка: блюдо не найдено.")

    menu_manager.delete_dish_by_id(dish_id)
    print(f"Блюдо '{dish}' удалено.")


@run_safe_ui
def edit_dish_ui():
    dish_id = ask_input("ID блюда для изменения: ", is_num=True)
    dish = menu_manager.get_dish_by_id(dish_id)
    if not dish: return print("Ошибка: блюдо не найдено.")

    old_name, old_desc, old_price, old_cat = dish
    print(f"\nТекущее: {old_name} | {old_desc} | {old_price} руб. | Кат: {old_cat}\nОставьте пустым для сохранения.")

    name = ask_input(f"Название [{old_name}]: ", default=old_name)
    description = ask_input(f"Описание [{old_desc}]: ", default=old_desc)
    price = ask_input(f"Цена [{old_price}]: ", default=old_price, is_float=True)

    valid_cats = show_categories_ui()
    category_id = ask_input(f"ID категории [{old_cat}]: ", default=old_cat, is_num=True)

    if not price or price <= 0 or category_id not in valid_cats:
        return print("Ошибка: неверная цена или категория.")

    menu_manager.update_dish(dish_id, name, description, price, category_id)
    print(f"Блюдо с ID {dish_id} изменено.")


def show_db_ui():
    db_data = menu_manager.get_all_tables_data()
    if not db_data: return print("\nВ базе данных нет таблиц.")

    print(f"\n============================================================\nФайл: {menu_manager.DB_PATH}")
    for table_name, (columns, rows) in db_data.items():
        print(f"\n------------------------------------------------------------\nТаблица: {table_name}")
        if not rows: continue

        widths = [max(len(str(col)), max((len(str(row[i])) for row in rows), default=0)) for i, col in
                  enumerate(columns)]
        header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * w for w in widths)

        print(header + "\n" + separator)
        for row in rows:
            print(" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)))


def main():
    db_file_path = PROJECT_ROOT / "database" / "capycafe.db"

    if not db_file_path.exists():
        print("База данных не обнаружена. Запуск первичной инициализации...")
        insert_path = PROJECT_ROOT / "database" / "scripts" / "createdb" / "insert_db.py"
        subprocess.run([sys.executable, str(insert_path)])
    else:
        print("База данных успешно обнаружена. Пропуск инициализации.")

    actions = {"1": add_dish_ui, "2": delete_dish_ui, "3": edit_dish_ui, "4": show_db_ui}
    while True:
        print("\n1. Добавить блюдо\n2. Удалить блюдо\n3. Изменить блюдо\n4. Просмотреть БД\n0. Выход")
        choice = input("Выберите действие: ").strip()
        if choice == "0": break

        action = actions.get(choice)
        if action:
            action()
        else:
            print("Ошибка: неизвестный пункт меню.")


if __name__ == "__main__":
    main()
