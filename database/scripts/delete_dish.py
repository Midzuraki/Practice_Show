import sqlite3
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = CURRENT_DIR
while os.path.basename(BASE_DIR) != "practice3" and BASE_DIR != os.path.dirname(BASE_DIR):
    BASE_DIR = os.path.dirname(BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "database", "capycafe.db")

def delete_dish():
    print("--- УДАЛЕНИЕ БЛЮДА ИЗ МЕНЮ ---")

    dish_id = input("Введите ID блюда для удаления: ")
    if not dish_id.isdigit():
        print("Ошибка: ID должен быть числом.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Проверка существования блюда
        cursor.execute("SELECT name FROM dishes WHERE id = ?;", (dish_id,))
        dish = cursor.fetchone()

        if not dish:
            print("Ошибка: Блюдо с таким ID не найдено в меню.")
            return

        # Удаление записи
        cursor.execute("DELETE FROM dishes WHERE id = ?;", (dish_id,))
        conn.commit()
        print(f"\nУспешно: Блюдо '{dish[0]}' (ID: {dish_id}) удалено из базы данных.")

    except sqlite3.Error as e:
        print(f"\nОшибка удаления: {e}\n(Примечание: Если сработало ограничение RESTRICT, значит блюдо использовано в заказах. Измените его флаг is_available на 0).")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    delete_dish()
