import sys
import sqlite3
from pathlib import Path

if getattr(sys, 'frozen', False):
    # Если запущен .exe
    EXE_DIR = Path(sys.executable).resolve().parent  # Папка CapyCafe/
    PROJECT_ROOT = EXE_DIR.parent  # Корень practice3/
else:
    # Если запущен обычный .py
    MAIN_DIR = Path(__file__).resolve().parent  # Папка main/
    PROJECT_ROOT = MAIN_DIR.parent  # Корень practice3/

DB_PATH = PROJECT_ROOT / "database" / "capycafe.db"

# Исправляем поиск модулей для импорта папки database
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- ДАЛЕЕ ВАШИ ИМПОРТЫ ---
from database.scripts.dishes import menu_manager
from database.scripts.authorization import user_manager
from database.scripts.orders import order_manager
from database.scripts.reports import report_manager

menu_manager.DB_PATH = DB_PATH
user_manager.DB_PATH = DB_PATH
order_manager.DB_PATH = DB_PATH
report_manager.DB_PATH = DB_PATH

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
        except ValueError as e:
            print(f"Ошибка: {e}" if str(e) else "Ошибка: Некорректный ввод данных.")
        except TypeError:
            print("Ошибка: Некорректный ввод данных.")
        except sqlite3.IntegrityError as e:
            print(f"Ошибка операции БД (отклонено базой): {e}")
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")

    return wrapper


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
        try:
            menu_manager.delete_dish_by_id(uid)
        except sqlite3.IntegrityError:
            if not menu_manager.dish_is_used(uid):
                raise
            print("Блюдо использовано в заказах и не может быть удалено.")
            if input("Отметить блюдо как недоступное? (д/н): ").strip().lower() == "д":
                menu_manager.set_dish_availability(uid, False)
                print("Блюдо отмечено как недоступное.")
            return
    elif target == "user":
        if uid == CURRENT_USER[0]: return print("Ошибка: Нельзя удалить себя.")
        user_manager.delete_user_by_id(uid)
    elif target == "order":
        order_manager.cancel_order(uid)
        return print(f"Заказ №{uid} отменён.")
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



@run_safe_ui
def ui_categories():
    categories = menu_manager.get_categories()
    if not categories:
        print("Категорий нет.")
        return
    print("\nКАТЕГОРИИ")
    for category_id, name in categories:
        print(f"  {category_id}. {name}")


@run_safe_ui
def ui_add_category():
    name = ask("Название новой категории: ")
    if name:
        category_id = menu_manager.add_category(name)
        print(f"Категория добавлена. ID: {category_id}")


@run_safe_ui
def ui_edit_category():
    ui_categories()
    category_id = ask("ID категории для переименования: ", is_num=True)
    if not category_id:
        return
    current = next((name for cid, name in menu_manager.get_categories() if cid == category_id), None)
    if current is None:
        print("Категория не найдена.")
        return
    name = ask(f"Новое название [{current}]: ", default=current)
    menu_manager.rename_category(category_id, name)
    print("Категория переименована.")


@run_safe_ui
def ui_delete_category():
    ui_categories()
    category_id = ask("ID категории для удаления: ", is_num=True)
    if not category_id:
        return
    menu_manager.delete_category(category_id)
    print("Категория удалена.")


@run_safe_ui
def ui_edit_user():
    list_users_formatted_ui()
    employee_id = ask("ID сотрудника для изменения: ", is_num=True)
    employee = user_manager.get_user_by_id(employee_id) if employee_id else None
    if not employee:
        print("Сотрудник не найден.")
        return
    name = ask(f"ФИО [{employee[1]}]: ", default=employee[1])
    positions = user_manager.get_valid_positions()
    print("Должности:", ", ".join(positions))
    position = ask(f"Должность [{employee[2]}]: ", default=employee[2])
    user_manager.update_user(employee_id, name, position)
    print("Данные сотрудника изменены.")


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
    print("\n" + "=" * 55 + "\n               МЕНЮ КАФЕ «ПРИЧАЛ»\n" + "=" * 55)
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


@run_safe_ui
def ui_search_dishes():
    part = input("Часть названия (Enter - все): ")
    print("Категории:", menu_manager.get_categories())
    raw_cat = input("ID категории (Enter - все): ").strip()
    cat_id = int(raw_cat) if raw_cat else None
    raw_sort = input("Сортировка по цене (1 - по возрастанию, 2 - по убыванию, Enter - без): ").strip()
    rows = menu_manager.get_dishes(cat_id, part, {"1": "asc", "2": "desc"}.get(raw_sort))
    if not rows: return print("Ничего не найдено.")
    for d_id, name, cat, price, avail in rows:
        print(f" [{d_id}] {name} | {cat} | {price} руб. | {'в наличии' if avail else 'нет в наличии'}")


@run_safe_ui
def ui_filter_orders():
    statuses = order_manager.get_statuses()
    for s in statuses: print(f"  {s[0]} - {s[1]}")
    raw_status = input("ID статуса (Enter - все): ").strip()
    status_id = int(raw_status) if raw_status else None
    d_from = input("Дата с (ДД.ММ.ГГГГ, Enter - без ограничения): ").strip() or None
    d_to = input("Дата по (ДД.ММ.ГГГГ, Enter - без ограничения): ").strip() or None
    orders = order_manager.get_orders(status_id, d_from, d_to)
    if not orders: return print("Заказов не найдено.")
    for o in orders:
        print(f" №{o[0]} | {o[1]} | стол {o[2]} | {o[3]} | {o[4]} | {o[5]} руб.")


@run_safe_ui
def ui_order_details():
    oid = ask("ID заказа: ", is_num=True)
    if not oid or not order_manager.get_order_info(oid): return print("Ошибка: Заказ не найден.")
    for name, qty, price, total in order_manager.get_order_items_details(oid):
        print(f" {name} | {qty} x {price} = {total}")
    print(f"Итого: {order_manager.get_order_total(oid)} руб.")


@run_safe_ui
def ui_dish_rating():
    rows = report_manager.get_dish_rating()
    if not rows: return print("Данных нет.")
    for name, sold, revenue in rows:
        print(f" {name} | порций: {sold} | выручка: {revenue}")


@run_safe_ui
def ui_revenue():
    d_from = input("Дата начала (ДД.ММ.ГГГГ): ").strip()
    d_to = input("Дата окончания (Enter - только одна дата): ").strip() or None
    count, total = report_manager.get_revenue(d_from, d_to)
    print(f"Период: {d_from} - {d_to or d_from}. Оплаченных заказов: {count}. Выручка: {total} руб.")


def main():
    global CURRENT_USER

    # 1. Жесткое разделение путей для работы в IDE и в скомпилированном .exe
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.argv[0]).resolve().parent
        db_file_path = exe_dir.parent / "database" / "capycafe.db"
    else:
        db_file_path = DB_PATH

    # Компактные встроенные SQL-скрипты автоматического развертывания структуры и данных кафе
    sql_tables = "PRAGMA foreign_keys = ON; CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE); CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, position TEXT NOT NULL); CREATE TABLE IF NOT EXISTS order_statuses (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE); CREATE TABLE IF NOT EXISTS dishes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, price REAL NOT NULL, is_available INTEGER NOT NULL DEFAULT 1, category_id INTEGER NOT NULL, FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT, CONSTRAINT chk_dish_price CHECK (price > 0)); CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), table_number INTEGER NOT NULL, employee_id INTEGER NOT NULL, status_id INTEGER NOT NULL, FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT, FOREIGN KEY (status_id) REFERENCES order_statuses(id) ON DELETE RESTRICT, CONSTRAINT chk_table_number CHECK (table_number BETWEEN 1 AND 12)); CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, dish_id INTEGER NOT NULL, quantity INTEGER NOT NULL, price_at_order REAL NOT NULL, FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE, FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE RESTRICT, CONSTRAINT chk_item_quantity CHECK (quantity > 0), CONSTRAINT chk_item_price CHECK (price_at_order > 0), UNIQUE(order_id, dish_id));"
    sql_data = "PRAGMA foreign_keys = ON; INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'Закуски'), (2, 'Салаты'), (3, 'Супы'), (4, 'Горячие блюда'), (5, 'Десерты'), (6, 'Напитки'); INSERT OR IGNORE INTO employees (id, full_name, position) VALUES (1, 'Иванов Иван Иванович', 'Официант'), (2, 'Петрова Анна Сергеевна', 'Официант'), (3, 'Сидоров Алексей Петрович', 'Повар'), (4, 'Кузнецов Дмитрий Владимирович', 'Бармен'), (5, 'Смирнова Елена Николаевна', 'Администратор'); INSERT OR IGNORE INTO order_statuses (id, name) VALUES (1, 'Принят'), (2, 'Готовится'), (3, 'Готов'), (4, 'Выдан'), (5, 'Оплачен'), (6, 'Отменён'); INSERT OR IGNORE INTO dishes (id, name, description, price, is_available, category_id) VALUES (1, 'Гренки чесночные', 'Ржаные гренки с чесночным соусом', 150.00, 1, 1), (2, 'Салат Цезарь', 'Классический салат с курицей', 350.00, 1, 2), (3, 'Уха Астраханская', 'Традиционный суп из местной рыбы', 400.00, 1, 3), (4, 'Борщ', 'Классический мясной борщ со сметаной', 300.00, 1, 3), (5, 'Стейк из судака', 'Судак на гриле с овощами', 550.00, 1, 4), (6, 'Котлеты по-киевски', 'С картофельным пюре', 450.00, 1, 4), (7, 'Торт Наполеон', 'Домашний слоеный торт', 250.00, 1, 5), (8, 'Морс ягодный', 'Собственного приготовления', 100.00, 1, 6), (9, 'Кофе Капучино', 'Классический кофейный напиток', 180.00, 0, 6); INSERT OR IGNORE INTO orders (id, order_date, table_number, employee_id, status_id) VALUES (1, '2026-10-01 13:15:00', 3, 1, 5), (2, '2026-10-07 19:30:00', 5, 2, 2), (3, '2026-10-07 20:00:00', 12, 1, 1); INSERT OR IGNORE INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (1, 1, 2, 150.00), (1, 3, 1, 400.00), (2, 2, 1, 350.00), (2, 6, 2, 450.00), (3, 5, 1, 550.00), (3, 7, 2, 250.00), (3, 8, 3, 100.00);"

    # 2. Проверяем не просто наличие файла, а наличие таблиц в СУБД
    db_is_ready = False
    if db_file_path.exists():
        try:
            with sqlite3.connect(db_file_path) as conn:
                conn.execute("SELECT id FROM employees LIMIT 1")
                db_is_ready = True
        except sqlite3.Error:
            pass

    # 3. Автоматическая автосборка СУБД, если база пуста или отсутствует
    if not db_is_ready:
        print("\nБаза данных не инициализирована. Запуск встроенной автосборки СУБД...")
        try:
            db_file_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db_file_path) as conn:
                conn.executescript(sql_tables)
                conn.executescript(sql_data)
            print(f"УСПЕХ: База данных успешно сгенерирована по пути:\n -> {db_file_path}")
        except Exception as e:
            print(f"Критическая ошибка автосборки базы: {e}")
            input("\nНажмите Enter для выхода...")
            return
    else:
        print(f"База данных успешно обнаружена и проверена:\n -> {db_file_path}")

    # Выбор сотрудника используется для фиксации автора заказа; авторизация не реализована.
    employees = user_manager.get_all_users()
    if not employees:
        print("В базе нет сотрудников. Добавьте сотрудника в базу данных и запустите программу повторно.")
        return
    print("\nВыберите сотрудника, от имени которого будут оформляться заказы:")
    for employee_id, full_name, position in employees:
        print(f"  {employee_id}. {full_name} — {position}")
    while CURRENT_USER is None:
        employee_id = ask("ID сотрудника: ", is_num=True)
        CURRENT_USER = user_manager.get_user_by_id(employee_id) if employee_id else None
        if CURRENT_USER is None:
            print("Сотрудник не найден. Повторите ввод.")
    print(f"Выбран сотрудник: {CURRENT_USER[1]}. Разграничение доступа по должностям не используется.")

    menu = {
        "1": ("Просмотр структуры БД", show_db_ui),
        "2": ("Просмотр меню кафе", ui_show_cafe_menu),
        "3": ("Добавить блюдо", lambda: ui_add_entity("dish")),
        "4": ("Изменить блюдо", ui_edit_dish),
        "5": ("Удалить блюдо", lambda: ui_delete_entity("dish")),
        "6": ("Поиск, фильтр и сортировка блюд", ui_search_dishes),
        "7": ("Список категорий", ui_categories),
        "8": ("Добавить категорию", ui_add_category),
        "9": ("Переименовать категорию", ui_edit_category),
        "10": ("Удалить категорию", ui_delete_category),
        "11": ("Добавить сотрудника", lambda: ui_add_entity("user")),
        "12": ("Изменить сотрудника", ui_edit_user),
        "13": ("Удалить сотрудника", lambda: ui_delete_entity("user")),
        "14": ("Список сотрудников", list_users_formatted_ui),
        "15": ("Оформить новый заказ", lambda: ui_add_entity("order")),
        "16": ("Отменить заказ", lambda: ui_delete_entity("order")),
        "17": ("Просмотреть активные заказы", ui_list_orders),
        "18": ("Изменить статус заказа", ui_change_status),
        "19": ("Список заказов с фильтром", ui_filter_orders),
        "20": ("Состав и сумма заказа", ui_order_details),
        "21": ("Рейтинг блюд", ui_dish_rating),
        "22": ("Выручка за период", ui_revenue),
    }

    while True:
        print("\n=== ИНФОРМАЦИОННАЯ СИСТЕМА КАФЕ «ПРИЧАЛ» ===")
        for key, (label, _) in menu.items():
            print(f"{key}. {label}")
        print("0. Выход")
        choice = input("\nВыберите действие: ").strip()
        if choice == "0":
            break
        if choice in menu:
            menu[choice][1]()
        else:
            print("Ошибка: неизвестный пункт меню.")

if __name__ == "__main__":
    main()
