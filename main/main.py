import sys
import sqlite3
import subprocess
from pathlib import Path

# Универсальное определение путей для работы в IDE и в собранном .exe
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

# Подключаем пути к модулям СУБД
for folder in ["dishes", "authorization", "orders"]:
    sys.path.append(str(PROJECT_ROOT / "database" / "scripts" / folder))

import menu_manager
import user_manager
import order_manager

CURRENT_USER = None  # (id, full_name, position)

def ask(prompt, default=None, is_num=False, is_float=False):
    val = input(prompt).strip()
    if not val and default is not None: return default
    try:
        return float(val) if is_float else (int(val) if is_num else val)
    except ValueError:
        return None


def run_safe_ui(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError):
            print("Ошибка: Некорректный ввод данных.")
        except sqlite3.IntegrityError as e:
            print(f"Ошибка операции БД (отклонено базой): {e}")
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")

    return wrapper


def login_screen():
    global CURRENT_USER
    print("\n" + "=" * 40 + "\n   ВХОД В ИНФОРМАЦИОННУЮ СИСТЕМУ КАФЕ\n" + "=" * 40)
    try:
        users = user_manager.get_all_users()
        print("Доступные ID для входа:")
        for u in users: print(f"  ID: {u[0]} — {u[1]} ({u[2]})")
    except Exception:
        pass

    uid = ask("\nВведите ваш ID сотрудника: ", is_num=True)
    user = user_manager.get_user_by_id(uid) if uid else None
    if not user: print("Ошибка: Сотрудник не найден."); return False
    CURRENT_USER = user
    print(f"\nДобро пожаловать, {user[1]} ({user[2]})")
    return True


@run_safe_ui
def ui_add_entity(target):
    if target == "dish":
        cats = {r[0] for r in menu_manager.get_categories()}
        print("Категории:", [r for r in menu_manager.get_categories()])
        cat_id = ask("ID категории: ", is_num=True)
        if cat_id not in cats: return print("Ошибка: Категории не существует.")
        name = ask("Название: ")
        price = ask("Цена: ", is_float=True)
        if name and price and price > 0:
            print(f"Блюдо добавлено. ID: {menu_manager.insert_dish(name, ask('Описание: '), price, cat_id)}")

    elif target == "user":
        name = ask("ФИО сотрудника: ")
        roles = user_manager.get_valid_positions()
        for idx, r in enumerate(roles, 1): print(f"  {idx}. {r}")
        r_idx = ask("Выберите номер роли: ", is_num=True)
        if name and r_idx and (1 <= r_idx <= len(roles)):
            print(f"Сотрудник добавлен. ID: {user_manager.insert_user(name, roles[r_idx - 1])}")

    elif target == "order":
        table = ask("Номер стола (1-12): ", is_num=True)
        if not table or not (1 <= table <= 12): return print("Неверный стол.")
        items = []
        while True:
            did = ask("ID блюда (0 для завершения): ", is_num=True)
            if did == 0: break
            qty = ask("Количество: ", is_num=True)
            if did and qty and qty > 0: items.append((did, qty))
        if items: print(f"Заказ оформлен. ID: {order_manager.create_order(table, CURRENT_USER[0], items)}")


@run_safe_ui
def ui_delete_entity(target):
    uid = ask(f"Введите ID {target} для удаления: ", is_num=True)
    if not uid: return
    if target == "dish":
        menu_manager.delete_dish_by_id(uid)
    elif target == "user":
        if uid == CURRENT_USER[0]: return print("Ошибка: Нельзя удалить себя.")
        user_manager.delete_user_by_id(uid)
    elif target == "order":
        order_manager.delete_order_by_id(uid)
    print("Успешно удалено.")


@run_safe_ui
def ui_edit_dish():
    did = ask("ID блюда для изменения: ", is_num=True)
    dish = menu_manager.get_dish_by_id(did)
    if not dish: return print("Блюдо не найдено.")
    name = ask(f"Название [{dish[0]}]: ", default=dish[0])
    desc = ask(f"Описание [{dish[1]}]: ", default=dish[1])
    price = ask(f"Цена [{dish[2]}]: ", default=dish[2], is_float=True)
    cat = ask(f"Категория [{dish[3]}]: ", default=dish[3], is_num=True)
    menu_manager.update_dish(did, name, desc, price, cat)
    print("Блюдо изменено.")


def show_db_ui():
    for name, (cols, rows) in menu_manager.get_all_tables_data().items():
        print(f"\nТаблица: {name}")
        if not rows: print("(Пусто)"); continue
        widths = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
        print(" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)))
        for r in rows: print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))


def ui_show_cafe_menu():
    dishes = menu_manager.get_active_menu()
    if not dishes: return print("\n[Меню кафе пустое]")
    print("\n" + "=" * 55 + "\n               МЕНЮ КАФЕ CAPYCAFE\n" + "=" * 55)
    current_cat = ""
    for d_id, name, desc, price, cat_name in dishes:
        if cat_name != current_cat:
            current_cat = cat_name
            print(f"\n--- {current_cat.upper()} ---")
        print(f" [{d_id}] {name.ljust(25)} | {str(price).rjust(6)} руб. ({desc})")
    print("=" * 55)


def list_users_formatted_ui():
    users = user_manager.get_all_users()
    if not users: return print("\n[Сотрудников нет]")
    print("\n" + "-" * 55 + "\nСПИСОК СОТРУДНИКОВ КАФЕ\n" + "-" * 55)
    headers = ["ID", "ФИО Сотрудника", "Должность"]
    widths = [max(len(headers[i]), max(len(str(u[i])) for u in users)) for i in range(3)]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(3)) + "\n" + "-+-".join("-" * w for w in widths))
    for u in users: print(" | ".join(str(u[i]).ljust(widths[i]) for i in range(3)))


def ui_list_orders():
    """Выводит только активные заказы в работе персоналу"""
    orders = order_manager.get_active_orders()
    if not orders: return print("\n[Сейчас нет активных заказов в работе]")
    print("\n" + "-" * 65 + "\nСПИСОК АКТИВНЫХ ЗАКАЗОВ (В РАБОТЕ)\n" + "-" * 65)
    headers = ["ID Заказа", "Дата/Время", "Стол", "Официант", "Статус"]
    widths = [max(len(headers[i]), max(len(str(o[i])) for o in orders)) for i in range(5)]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(5)) + "\n" + "-+-".join("-" * w for w in widths))
    for o in orders: print(" | ".join(str(o[i]).ljust(widths[i]) for i in range(5)))


@run_safe_ui
def ui_change_status():
    ui_list_orders()
    orders = order_manager.get_active_orders()
    if not orders: return

    oid = ask("\nВведите ID заказа для изменения статуса: ", is_num=True)
    if not oid or not order_manager.get_order_info(oid): return print("Ошибка: Заказ не найден.")

    statuses = order_manager.get_statuses()
    print("\nДоступные статусы:")
    for s in statuses: print(f"  {s[0]} - {s[1]}")

    sid = ask("Выберите номер нового статуса: ", is_num=True)
    if sid not in {s[0] for s in statuses}: return print("Ошибка: Неверный статус.")

    order_manager.update_order_status(oid, sid)
    print(f"Статус заказа №{oid} успешно изменен!")


def main():
    global CURRENT_USER

    # 1. Разделяем пути для базы (снаружи) и для SQL-схем (внутри .exe)
    if getattr(sys, 'frozen', False):
        # Если это .exe, схемы лежат во внутренней папке _internal/database
        BASE_SQL_DIR = Path(sys._MEIPASS) / "database"
        db_file_path = Path(sys.executable).resolve().parent.parent / "database" / "capycafe.db"
    else:
        # Если запускаем в IDE
        BASE_SQL_DIR = PROJECT_ROOT / "database"
        db_file_path = PROJECT_ROOT / "database" / "capycafe.db"

    # 2. Проверяем готовность базы данных
    db_is_ready = False
    if db_file_path.exists():
        try:
            with sqlite3.connect(db_file_path) as conn:
                conn.execute("SELECT id FROM employees LIMIT 1")
                db_is_ready = True
        except sqlite3.Error:
            pass

    # 3. Автоматическая сборка, если база пуста или отсутствует
    if not db_is_ready:
        print("\nБаза данных не инициализирована. Сборка СУБД из конфигурационных файлов...")
        try:
            db_file_path.parent.mkdir(parents=True, exist_ok=True)

            schema_file = BASE_SQL_DIR / "schema.sql"
            data_file = BASE_SQL_DIR / "data.sql"

            if not schema_file.exists() or not data_file.exists():
                print(f"Критическая ошибка: Не найдены файлы конфигурации SQL в {BASE_SQL_DIR}")
                input("\nНажмите Enter для выхода...");
                return

            schema_sql = schema_file.read_text(encoding="utf-8")
            data_sql = data_file.read_text(encoding="utf-8")

            with sqlite3.connect(db_file_path) as conn:
                conn.executescript(schema_sql)
                conn.executescript(data_sql)
            print("УСПЕХ: База данных 'capycafe.db' успешно сгенерирована!")
        except Exception as e:
            print(f"Критическая ошибка автосборки базы: {e}")
            input("\nНажмите Enter для выхода...");
            return
    else:
        print("База данных успешно обнаружена и проверена.")

    # 4. Аутентификация сотрудника
    while not CURRENT_USER:
        login_screen()

    role = CURRENT_USER

    admin_menu = {
        "1": ("Просмотр структуры БД (Сырые таблицы)", show_db_ui),
        "2": ("Просмотреть актуальное Меню кафе", ui_show_cafe_menu),
        "3": ("Добавить блюдо в меню", lambda: ui_add_entity("dish")),
        "4": ("Изменить блюдо в меню", ui_edit_dish),
        "5": ("Удалить блюдо из меню", lambda: ui_delete_entity("dish")),
        "6": ("Добавить нового сотрудника", lambda: ui_add_entity("user")),
        "7": ("Удалить сотрудника", lambda: ui_delete_entity("user")),
        "8": ("Список сотрудников", list_users_formatted_ui),
        "9": ("Оформить новый заказ", lambda: ui_add_entity("order")),
        "10": ("Удалить заказ", lambda: ui_delete_entity("order")),
        "11": ("Просмотреть active заказы", ui_list_orders),
        "12": ("Изменить статус заказа", ui_change_status)
    }
    waiter_menu = {
        "1": ("Просмотреть Меню кафе", ui_show_cafe_menu),
        "2": ("Оформить новый заказ", lambda: ui_add_entity("order")),
        "3": ("Удалить заказ", lambda: ui_delete_entity("order")),
        "4": ("Просмотреть активные заказы", ui_list_orders)
    }
    kitchen_menu = {
        "1": ("Просмотреть Меню кафе", ui_show_cafe_menu),
        "2": ("Просмотреть активные заказы", ui_list_orders),
        "3": ("Изменить статус заказа (Отметка о готовности)", ui_change_status)
    }

    if role == 'Администратор':
        menu = admin_menu
    elif role == 'Официант':
        menu = waiter_menu
    elif role in ['Повар', 'Бармен']:
        menu = kitchen_menu
    else:
        menu = {"1": ("Просмотреть Меню кафе", ui_show_cafe_menu)}

    while True:
        print(f"\n=== МЕНЮ ({CURRENT_USER} | Роль: {role}) ===")
        for k, v in menu.items(): print(f"{k}. {v}")
        print("0. Выход")

        ch = input("\nВыберите действие: ").strip()
        if ch == "0": break
        if ch in menu:
            menu[ch]()
        else:
            print("Ошибка: Пункт меню недоступен.")


if __name__ == "__main__":
    main()
