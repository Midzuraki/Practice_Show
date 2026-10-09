import io
import sys
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "database").exists()), Path(__file__).resolve().parent.parent)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.scripts.dishes import menu_manager
from database.scripts.orders import order_manager
from database.scripts.authorization import user_manager, login
from database.scripts.reports import report_manager

DB_DIR = PROJECT_ROOT / "database"
MODULES = (menu_manager, order_manager, user_manager, login, report_manager)

ACCEPTED, COOKING, READY, SERVED, PAID, CANCELLED = 1, 2, 3, 4, 5, 6
WAITER, WAITER2, COOK, BARMAN, ADMIN = 1, 2, 3, 4, 5


class BaseDbTest(unittest.TestCase):
    """Каждый тест работает с чистой временной базой, собранной из schema.sql и data.sql (НФТ-9)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self._tmp.name) / "test.db"
        conn = sqlite3.connect(self.db_path)
        conn.executescript((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((DB_DIR / "data.sql").read_text(encoding="utf-8"))
        conn.commit()
        conn.close()
        self._old_paths = [m.DB_PATH for m in MODULES]
        for m in MODULES:
            m.DB_PATH = self.db_path

    def tearDown(self):
        for m, old in zip(MODULES, self._old_paths):
            m.DB_PATH = old
        self._tmp.cleanup()

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def execute(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def set_status(self, order_id, status_id):
        self.execute("UPDATE orders SET status_id = ? WHERE id = ?", (status_id, order_id))

    def status_of(self, order_id):
        return self.query("SELECT status_id FROM orders WHERE id = ?", (order_id,))[0][0]

    def count(self, table):
        return self.query(f"SELECT COUNT(*) FROM {table}")[0][0]


class TestDatabaseConstraints(BaseDbTest):
    """НФТ-1, НФТ-5, таблица 7: ограничения на уровне СУБД."""

    def assertRejected(self, sql, params=()):
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute(sql, params)

    def test_dish_price_negative_rejected(self):
        self.assertRejected("INSERT INTO dishes (name, price, category_id) VALUES ('Суп', -50.00, 3)")

    def test_dish_price_zero_rejected(self):
        self.assertRejected("INSERT INTO dishes (name, price, category_id) VALUES ('Суп', 0, 3)")

    def test_dish_price_minimal_positive_accepted(self):
        self.execute("INSERT INTO dishes (name, price, category_id) VALUES ('Суп', 0.01, 3)")

    def test_dish_without_name_rejected(self):
        self.assertRejected("INSERT INTO dishes (name, price, category_id) VALUES (NULL, 10, 3)")

    def test_dish_unknown_category_rejected(self):
        self.assertRejected("INSERT INTO dishes (name, price, category_id) VALUES ('Суп', 10, 99)")

    def test_table_number_out_of_range_rejected(self):
        for table in (0, 13, 25, -1):
            with self.subTest(table=table):
                self.assertRejected("INSERT INTO orders (table_number, employee_id, status_id) VALUES (?, 1, 1)", (table,))

    def test_table_number_boundaries_accepted(self):
        for table in (1, 12):
            with self.subTest(table=table):
                self.execute("INSERT INTO orders (table_number, employee_id, status_id) VALUES (?, 1, 1)", (table,))

    def test_order_unknown_employee_rejected(self):
        self.assertRejected("INSERT INTO orders (table_number, employee_id, status_id) VALUES (1, 99, 1)")

    def test_order_unknown_status_rejected(self):
        self.assertRejected("INSERT INTO orders (table_number, employee_id, status_id) VALUES (1, 1, 99)")

    def test_item_quantity_not_positive_rejected(self):
        for qty in (0, -1):
            with self.subTest(qty=qty):
                self.assertRejected(
                    "INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (3, 1, ?, 150)", (qty,))

    def test_item_price_not_positive_rejected(self):
        self.assertRejected("INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (3, 1, 1, 0)")

    def test_duplicate_dish_in_order_rejected(self):
        self.assertRejected("INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (3, 5, 1, 550)")

    def test_duplicate_category_rejected(self):
        self.assertRejected("INSERT INTO categories (name) VALUES ('Супы')")

    def test_category_with_dishes_not_deletable(self):
        self.assertRejected("DELETE FROM categories WHERE id = 3")

    def test_dish_used_in_orders_not_deletable(self):
        self.assertRejected("DELETE FROM dishes WHERE id = 1")

    def test_employee_with_orders_not_deletable(self):
        self.assertRejected("DELETE FROM employees WHERE id = 1")

    def test_order_delete_cascades_to_items(self):
        self.execute("DELETE FROM orders WHERE id = 3")
        self.assertEqual(self.query("SELECT COUNT(*) FROM order_items WHERE order_id = 3")[0][0], 0)

    def test_seed_data_loaded(self):
        self.assertEqual(self.count("categories"), 6)
        self.assertEqual(self.count("employees"), 5)
        self.assertEqual(self.count("order_statuses"), 6)
        self.assertEqual(self.count("dishes"), 9)
        self.assertEqual(self.count("orders"), 3)
        self.assertEqual(self.count("order_items"), 7)
        self.assertIn(("Салаты",), self.query("SELECT name FROM categories"))


class TestCategories(BaseDbTest):
    """ФТ-1, ФТ-2."""

    def test_list_categories(self):
        cats = menu_manager.get_categories()
        self.assertEqual(len(cats), 6)
        self.assertEqual(cats[0], (1, "Закуски"))

    def test_add_category(self):
        cid = menu_manager.add_category("  Завтраки ")
        self.assertIn((cid, "Завтраки"), menu_manager.get_categories())

    def test_add_category_empty_rejected(self):
        for name in ("", "   ", None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    menu_manager.add_category(name)

    def test_add_category_duplicate_rejected_case_insensitive(self):
        for name in ("Супы", "супы", " СУПЫ "):
            with self.subTest(name=name):
                with self.assertRaises(sqlite3.IntegrityError):
                    menu_manager.add_category(name)

    def test_rename_category(self):
        menu_manager.rename_category(1, "Холодные закуски")
        self.assertIn((1, "Холодные закуски"), menu_manager.get_categories())

    def test_rename_category_to_same_name_allowed(self):
        menu_manager.rename_category(1, "Закуски")

    def test_rename_category_to_existing_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            menu_manager.rename_category(1, "Супы")

    def test_rename_category_empty_or_missing_rejected(self):
        with self.assertRaises(ValueError):
            menu_manager.rename_category(1, " ")
        with self.assertRaises(ValueError):
            menu_manager.rename_category(99, "Новая")

    def test_delete_empty_category(self):
        cid = menu_manager.add_category("Пустая")
        menu_manager.delete_category(cid)
        self.assertNotIn((cid, "Пустая"), menu_manager.get_categories())

    def test_delete_category_with_dishes_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            menu_manager.delete_category(3)
        self.assertEqual(len(menu_manager.get_categories()), 6)

    def test_delete_missing_category_rejected(self):
        with self.assertRaises(ValueError):
            menu_manager.delete_category(99)


class TestDishes(BaseDbTest):
    """ФТ-3 ... ФТ-9, таблица 7."""

    def test_list_dishes_contains_category_price_availability(self):
        rows = menu_manager.get_dishes()
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[0], (1, "Гренки чесночные", "Закуски", 150.0, 1))
        self.assertEqual(rows[8][4], 0)

    def test_active_menu_excludes_unavailable(self):
        names = [r[1] for r in menu_manager.get_active_menu()]
        self.assertEqual(len(names), 8)
        self.assertNotIn("Кофе Капучино", names)

    def test_insert_dish_available_by_default(self):
        did = menu_manager.insert_dish("Чай", "Чёрный", 90, 6)
        self.assertEqual(menu_manager.get_dish_by_id(did), ("Чай", "Чёрный", 90.0, 6, 1))

    def test_insert_dish_minimal_price_accepted(self):
        self.assertTrue(menu_manager.insert_dish("Сахар", None, 0.01, 6))

    def test_insert_dish_invalid_price_rejected(self):
        for price in (0, -1, -0.01, "100", None, True, float("nan"), float("inf")):
            with self.subTest(price=price):
                with self.assertRaises(ValueError):
                    menu_manager.insert_dish("Чай", "", price, 6)
        self.assertEqual(self.count("dishes"), 9)

    def test_insert_dish_empty_name_rejected(self):
        for name in ("", "  ", None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    menu_manager.insert_dish(name, "", 10, 6)

    def test_insert_dish_unknown_category_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            menu_manager.insert_dish("Чай", "", 10, 99)
        self.assertEqual(self.count("dishes"), 9)

    def test_update_dish_price_and_availability(self):
        menu_manager.update_dish(1, "Гренки", "Описание", 175.5, 1, is_available=False)
        self.assertEqual(menu_manager.get_dish_by_id(1), ("Гренки", "Описание", 175.5, 1, 0))

    def test_update_dish_keeps_availability_when_not_given(self):
        menu_manager.update_dish(9, "Капучино", "", 200, 6)
        self.assertEqual(menu_manager.get_dish_by_id(9)[4], 0)

    def test_update_dish_invalid_rejected(self):
        with self.assertRaises(ValueError):
            menu_manager.update_dish(1, "Гренки", "", 0, 1)
        with self.assertRaises(ValueError):
            menu_manager.update_dish(1, "", "", 10, 1)
        with self.assertRaises(ValueError):
            menu_manager.update_dish(99, "Блюдо", "", 10, 1)
        with self.assertRaises(sqlite3.IntegrityError):
            menu_manager.update_dish(1, "Гренки", "", 10, 99)
        self.assertEqual(menu_manager.get_dish_by_id(1)[2], 150.0)

    def test_price_change_does_not_affect_old_orders(self):
        menu_manager.update_dish(1, "Гренки чесночные", "", 999, 1)
        self.assertEqual(order_manager.get_order_total(1), 700.0)

    def test_set_availability(self):
        menu_manager.set_dish_availability(1, False)
        self.assertNotIn(1, [r[0] for r in menu_manager.get_active_menu()])
        menu_manager.set_dish_availability(1, True)
        self.assertIn(1, [r[0] for r in menu_manager.get_active_menu()])
        with self.assertRaises(ValueError):
            menu_manager.set_dish_availability(99, True)

    def test_delete_unused_dish(self):
        self.assertFalse(menu_manager.dish_is_used(4))
        menu_manager.delete_dish_by_id(4)
        self.assertIsNone(menu_manager.get_dish_by_id(4))

    def test_delete_used_dish_rejected_and_can_be_deactivated(self):
        self.assertTrue(menu_manager.dish_is_used(1))
        with self.assertRaises(sqlite3.IntegrityError):
            menu_manager.delete_dish_by_id(1)
        self.assertIsNotNone(menu_manager.get_dish_by_id(1))
        menu_manager.set_dish_availability(1, False)
        self.assertEqual(menu_manager.get_dish_by_id(1)[4], 0)
        self.assertEqual(order_manager.get_order_total(1), 700.0)

    def test_delete_missing_dish_rejected(self):
        with self.assertRaises(ValueError):
            menu_manager.delete_dish_by_id(99)

    def test_search_by_part_of_name(self):
        self.assertEqual([r[1] for r in menu_manager.search_dishes("уха")], ["Уха Астраханская"])

    def test_search_case_insensitive_cyrillic(self):
        self.assertEqual(menu_manager.search_dishes("УХА"), menu_manager.search_dishes("уха"))
        self.assertEqual(len(menu_manager.search_dishes("САЛАТ")), 1)

    def test_search_part_in_middle_and_multiple_results(self):
        names = [r[1] for r in menu_manager.search_dishes("а")]
        self.assertGreater(len(names), 3)
        self.assertTrue(all("а" in n.lower() for n in names))

    def test_search_no_results(self):
        self.assertEqual(menu_manager.search_dishes("pizza"), [])

    def test_search_empty_returns_all(self):
        self.assertEqual(len(menu_manager.search_dishes("")), 9)
        self.assertEqual(len(menu_manager.search_dishes("   ")), 9)
        self.assertEqual(len(menu_manager.search_dishes(None)), 9)

    def test_search_special_characters_do_not_break(self):
        for text in ("%", "_", "'", '"; DROP TABLE dishes; --'):
            with self.subTest(text=text):
                self.assertEqual(menu_manager.search_dishes(text), [])
        self.assertEqual(self.count("dishes"), 9)

    def test_filter_by_category(self):
        rows = menu_manager.get_dishes(category_id=3)
        self.assertEqual({r[1] for r in rows}, {"Уха Астраханская", "Борщ"})
        self.assertTrue(all(r[2] == "Супы" for r in rows))

    def test_filter_by_empty_category(self):
        cid = menu_manager.add_category("Пустая")
        self.assertEqual(menu_manager.get_dishes(category_id=cid), [])

    def test_filter_by_unknown_category(self):
        self.assertEqual(menu_manager.get_dishes(category_id=99), [])

    def test_search_within_category(self):
        rows = menu_manager.get_dishes(category_id=3, search="борщ")
        self.assertEqual([r[1] for r in rows], ["Борщ"])
        self.assertEqual(menu_manager.get_dishes(category_id=1, search="борщ"), [])

    def test_sort_by_price_ascending_and_descending(self):
        asc = [r[3] for r in menu_manager.get_dishes(price_order="asc")]
        desc = [r[3] for r in menu_manager.get_dishes(price_order="desc")]
        self.assertEqual(asc, sorted(asc))
        self.assertEqual(desc, sorted(desc, reverse=True))
        self.assertEqual(asc[0], 100.0)
        self.assertEqual(desc[0], 550.0)

    def test_sort_invalid_direction_rejected(self):
        with self.assertRaises(ValueError):
            menu_manager.get_dishes(price_order="random")

    def test_all_tables_dump(self):
        data = menu_manager.get_all_tables_data()
        self.assertEqual(set(data), {"categories", "dishes", "employees", "order_items", "order_statuses", "orders"})


class TestOrderCreation(BaseDbTest):
    """ФТ-10, ФТ-11, ФТ-13, таблица 7."""

    def test_create_order_defaults(self):
        oid = order_manager.create_order(4, WAITER, [(1, 2), (4, 1)])
        info = order_manager.get_order_info(oid)
        self.assertEqual(info[2], 4)
        self.assertEqual(info[3], "Иванов Иван Иванович")
        self.assertEqual(info[4], "Принят")
        self.assertRegex(info[1], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_create_order_total_is_sum_of_items(self):
        oid = order_manager.create_order(4, WAITER, [(1, 2), (4, 1)])
        self.assertEqual(order_manager.get_order_total(oid), 600.0)
        details = order_manager.get_order_items_details(oid)
        self.assertEqual(details, [("Гренки чесночные", 2, 150.0, 300.0), ("Борщ", 1, 300.0, 300.0)])

    def test_create_order_table_boundaries(self):
        for table in (1, 12):
            with self.subTest(table=table):
                self.assertTrue(order_manager.create_order(table, WAITER, [(1, 1)]))

    def test_create_order_table_out_of_range_rejected(self):
        for table in (0, 13, -1, 100, None, "5", 2.5, True):
            with self.subTest(table=table):
                with self.assertRaises(ValueError):
                    order_manager.create_order(table, WAITER, [(1, 1)])
        self.assertEqual(self.count("orders"), 3)

    def test_create_order_unknown_employee_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.create_order(1, 99, [(1, 1)])
        self.assertEqual(self.count("orders"), 3)

    def test_create_order_by_cook_or_barman_rejected(self):
        for emp in (COOK, BARMAN):
            with self.subTest(emp=emp):
                with self.assertRaises(ValueError):
                    order_manager.create_order(1, emp, [(1, 1)])

    def test_create_order_by_admin_allowed(self):
        self.assertTrue(order_manager.create_order(1, ADMIN, [(1, 1)]))

    def test_create_order_without_items_rejected(self):
        for items in ([], None):
            with self.subTest(items=items):
                with self.assertRaises(ValueError):
                    order_manager.create_order(1, WAITER, items)
        self.assertEqual(self.count("orders"), 3)

    def test_create_order_invalid_quantity_rejected(self):
        for qty in (0, -1, 1.5, "2", None, True):
            with self.subTest(qty=qty):
                with self.assertRaises(ValueError):
                    order_manager.create_order(1, WAITER, [(1, qty)])
        self.assertEqual(self.count("orders"), 3)
        self.assertEqual(self.count("order_items"), 7)

    def test_create_order_unavailable_dish_rejected_atomically(self):
        with self.assertRaises(sqlite3.IntegrityError):
            order_manager.create_order(1, WAITER, [(1, 1), (9, 1)])
        self.assertEqual(self.count("orders"), 3)
        self.assertEqual(self.count("order_items"), 7)

    def test_create_order_unknown_dish_rejected_atomically(self):
        with self.assertRaises(sqlite3.IntegrityError):
            order_manager.create_order(1, WAITER, [(1, 1), (99, 1)])
        self.assertEqual(self.count("orders"), 3)
        self.assertEqual(self.count("order_items"), 7)

    def test_create_order_duplicate_dishes_are_merged(self):
        oid = order_manager.create_order(1, WAITER, [(1, 1), (1, 2)])
        self.assertEqual(self.query("SELECT quantity FROM order_items WHERE order_id = ?", (oid,)), [(3,)])

    def test_create_order_fixes_price_at_order(self):
        oid = order_manager.create_order(1, WAITER, [(1, 1)])
        menu_manager.update_dish(1, "Гренки чесночные", "", 500, 1)
        self.assertEqual(order_manager.get_order_total(oid), 150.0)

    def test_new_order_is_not_hardcoded_to_existing_ids(self):
        first = order_manager.create_order(1, WAITER, [(1, 1)])
        second = order_manager.create_order(1, WAITER, [(1, 1)])
        self.assertEqual(second, first + 1)

    def test_total_of_order_without_items_is_zero(self):
        self.execute("INSERT INTO orders (table_number, employee_id, status_id) VALUES (2, 1, 1)")
        oid = self.query("SELECT MAX(id) FROM orders")[0][0]
        self.assertEqual(order_manager.get_order_total(oid), 0)

    def test_order_info_for_missing_order(self):
        self.assertIsNone(order_manager.get_order_info(99))
        self.assertEqual(order_manager.get_order_items_details(99), [])


class TestOrderItems(BaseDbTest):
    """ФТ-11, ФТ-12, ФТ-13."""

    def test_add_new_item(self):
        order_manager.add_order_item(3, 4, 2)
        self.assertEqual(order_manager.get_order_total(3), 550 + 500 + 300 + 600.0)

    def test_add_existing_item_sums_quantity(self):
        order_manager.add_order_item(3, 5, 2)
        self.assertEqual(self.query("SELECT quantity FROM order_items WHERE order_id = 3 AND dish_id = 5"), [(3,)])

    def test_add_item_invalid_quantity_rejected(self):
        for qty in (0, -1, 2.5, "1", None):
            with self.subTest(qty=qty):
                with self.assertRaises(ValueError):
                    order_manager.add_order_item(3, 4, qty)

    def test_add_unavailable_or_unknown_dish_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            order_manager.add_order_item(3, 9, 1)
        with self.assertRaises(sqlite3.IntegrityError):
            order_manager.add_order_item(3, 99, 1)

    def test_add_item_to_unknown_order_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.add_order_item(99, 4, 1)

    def test_edit_not_allowed_for_paid_and_cancelled(self):
        for status in (PAID, CANCELLED):
            self.set_status(3, status)
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    order_manager.add_order_item(3, 4, 1)
                with self.assertRaises(ValueError):
                    order_manager.update_item_quantity(3, 5, 2)
                with self.assertRaises(ValueError):
                    order_manager.remove_order_item(3, 5)
        self.assertEqual(self.query("SELECT quantity FROM order_items WHERE order_id = 3 AND dish_id = 5"), [(1,)])

    def test_edit_allowed_in_active_statuses(self):
        for status in (ACCEPTED, COOKING, READY, SERVED):
            self.set_status(3, status)
            with self.subTest(status=status):
                order_manager.update_item_quantity(3, 5, 2)

    def test_update_quantity(self):
        order_manager.update_item_quantity(3, 5, 4)
        self.assertEqual(order_manager.get_order_total(3), 4 * 550 + 500 + 300.0)

    def test_update_quantity_invalid_rejected(self):
        for qty in (0, -3, 1.2, "5"):
            with self.subTest(qty=qty):
                with self.assertRaises(ValueError):
                    order_manager.update_item_quantity(3, 5, qty)

    def test_update_missing_item_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.update_item_quantity(3, 4, 1)

    def test_remove_item(self):
        order_manager.remove_order_item(3, 5)
        self.assertEqual(order_manager.get_order_total(3), 500 + 300.0)
        with self.assertRaises(ValueError):
            order_manager.remove_order_item(3, 5)

    def test_total_recalculated_after_changes(self):
        oid = order_manager.create_order(1, WAITER, [(1, 1)])
        order_manager.add_order_item(oid, 4, 1)
        self.assertEqual(order_manager.get_order_total(oid), 450.0)
        order_manager.remove_order_item(oid, 1)
        self.assertEqual(order_manager.get_order_total(oid), 300.0)


class TestOrderStatuses(BaseDbTest):
    """ФТ-14, ФТ-15, таблицы 2 и 4."""

    VALID = {(1, 2), (1, 6), (2, 3), (2, 6), (3, 4), (4, 5)}

    def test_transition_matrix_for_admin(self):
        for src in range(1, 7):
            for dst in range(1, 7):
                self.set_status(3, src)
                with self.subTest(src=src, dst=dst):
                    if (src, dst) in self.VALID:
                        order_manager.update_order_status(3, dst, "Администратор")
                        self.assertEqual(self.status_of(3), dst)
                    else:
                        with self.assertRaises(ValueError):
                            order_manager.update_order_status(3, dst, "Администратор")
                        self.assertEqual(self.status_of(3), src)

    def test_transition_matrix_without_role(self):
        for src, dst in ((1, 3), (1, 5), (3, 2), (5, 1), (6, 1)):
            self.set_status(3, src)
            with self.subTest(src=src, dst=dst):
                with self.assertRaises(ValueError):
                    order_manager.update_order_status(3, dst)

    def test_full_happy_path_with_roles(self):
        oid = order_manager.create_order(2, WAITER, [(1, 1)])
        order_manager.update_order_status(oid, COOKING, "Повар")
        order_manager.update_order_status(oid, READY, "Повар")
        order_manager.update_order_status(oid, SERVED, "Официант")
        order_manager.update_order_status(oid, PAID, "Официант")
        self.assertEqual(self.status_of(oid), PAID)

    def test_barman_can_cook(self):
        order_manager.update_order_status(3, COOKING, "Бармен")
        order_manager.update_order_status(3, READY, "Бармен")

    def test_cook_cannot_serve_pay_or_cancel(self):
        for src, dst in ((1, CANCELLED), (3, SERVED), (4, PAID)):
            self.set_status(3, src)
            for role in ("Повар", "Бармен"):
                with self.subTest(src=src, dst=dst, role=role):
                    with self.assertRaises(ValueError):
                        order_manager.update_order_status(3, dst, role)
                    self.assertEqual(self.status_of(3), src)

    def test_waiter_cannot_cook(self):
        with self.assertRaises(ValueError):
            order_manager.update_order_status(3, COOKING, "Официант")
        self.set_status(3, COOKING)
        with self.assertRaises(ValueError):
            order_manager.update_order_status(3, READY, "Официант")

    def test_waiter_can_serve_pay_and_cancel(self):
        self.set_status(3, READY)
        order_manager.update_order_status(3, SERVED, "Официант")
        order_manager.update_order_status(3, PAID, "Официант")
        order_manager.update_order_status(2, CANCELLED, "Официант")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.update_order_status(3, COOKING, "Гость")

    def test_unknown_order_or_status_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.update_order_status(99, COOKING)
        with self.assertRaises(ValueError):
            order_manager.update_order_status(3, 99)
        with self.assertRaises(ValueError):
            order_manager.update_order_status(3, 0)

    def test_cancel_allowed_only_before_ready(self):
        for src in (ACCEPTED, COOKING):
            self.set_status(3, src)
            order_manager.cancel_order(3, "Официант")
            self.assertEqual(self.status_of(3), CANCELLED)
        for src in (READY, SERVED, PAID, CANCELLED):
            self.set_status(3, src)
            with self.subTest(src=src):
                with self.assertRaises(ValueError):
                    order_manager.cancel_order(3, "Администратор")
                self.assertEqual(self.status_of(3), src)

    def test_cancelled_order_stays_in_database(self):
        order_manager.cancel_order(3, "Официант")
        self.assertIsNotNone(order_manager.get_order_info(3))
        self.assertEqual(len(order_manager.get_order_items_details(3)), 3)

    def test_orders_are_never_deleted(self):
        with self.assertRaises(ValueError):
            order_manager.delete_order_by_id(3)
        self.assertEqual(self.count("orders"), 3)

    def test_paid_and_cancelled_orders_hidden_from_active_list(self):
        ids = [o[0] for o in order_manager.get_active_orders()]
        self.assertEqual(ids, [3, 2])
        order_manager.cancel_order(3, "Администратор")
        self.assertEqual([o[0] for o in order_manager.get_active_orders()], [2])

    def test_statuses_reference(self):
        self.assertEqual([s[1] for s in order_manager.get_statuses()],
                         ["Принят", "Готовится", "Готов", "Выдан", "Оплачен", "Отменён"])


class TestOrderListing(BaseDbTest):
    """ФТ-16, ФТ-17, таблица 7 (параметры запросов)."""

    def test_all_orders_with_totals(self):
        rows = order_manager.get_orders()
        self.assertEqual([r[0] for r in rows], [3, 2, 1])
        totals = {r[0]: r[5] for r in rows}
        self.assertEqual(totals, {1: 700.0, 2: 1250.0, 3: 1350.0})
        self.assertEqual(rows[0][4], "Принят")

    def test_sort_by_date(self):
        self.assertEqual([r[0] for r in order_manager.get_orders(newest_first=False)], [1, 2, 3])

    def test_filter_by_status(self):
        self.assertEqual([r[0] for r in order_manager.get_orders(status_id=PAID)], [1])
        self.assertEqual([r[0] for r in order_manager.get_orders(status_id=COOKING)], [2])
        self.assertEqual(order_manager.get_orders(status_id=CANCELLED), [])

    def test_filter_by_single_date(self):
        rows = order_manager.get_orders(date_from="07.10.2026", date_to="07.10.2026")
        self.assertEqual([r[0] for r in rows], [3, 2])

    def test_filter_by_period_boundaries_inclusive(self):
        rows = order_manager.get_orders(date_from="01.10.2026", date_to="07.10.2026")
        self.assertEqual(len(rows), 3)
        rows = order_manager.get_orders(date_from="02.10.2026", date_to="06.10.2026")
        self.assertEqual(rows, [])

    def test_filter_open_ended(self):
        self.assertEqual([r[0] for r in order_manager.get_orders(date_from="02.10.2026")], [3, 2])
        self.assertEqual([r[0] for r in order_manager.get_orders(date_to="01.10.2026")], [1])

    def test_filter_status_and_date_combined(self):
        rows = order_manager.get_orders(status_id=ACCEPTED, date_from="07.10.2026", date_to="07.10.2026")
        self.assertEqual([r[0] for r in rows], [3])
        self.assertEqual(order_manager.get_orders(status_id=PAID, date_from="07.10.2026"), [])

    def test_filter_start_after_end_rejected(self):
        with self.assertRaises(ValueError):
            order_manager.get_orders(date_from="08.10.2026", date_to="01.10.2026")

    def test_filter_invalid_date_format_rejected(self):
        for text in ("2026-10-07", "07/10/2026", "32.01.2026", "00.10.2026", "07.13.2026", "abc", "29.02.2026"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    order_manager.get_orders(date_from=text)

    def test_valid_leap_day_accepted(self):
        self.assertEqual(order_manager.parse_date("29.02.2028"), "2028-02-29")

    def test_order_composition_and_total(self):
        details = order_manager.get_order_items_details(1)
        self.assertEqual(details, [("Гренки чесночные", 2, 150.0, 300.0), ("Уха Астраханская", 1, 400.0, 400.0)])
        self.assertEqual(sum(d[3] for d in details), order_manager.get_order_total(1))


class TestReports(BaseDbTest):
    """ФТ-19, ФТ-20."""

    def test_rating_sorted_by_portions_descending(self):
        rating = report_manager.get_dish_rating()
        sold = [r[1] for r in rating]
        self.assertEqual(sold, sorted(sold, reverse=True))
        self.assertEqual(rating[0], ("Морс ягодный", 3, 300.0))

    def test_rating_contains_revenue_per_dish(self):
        rating = {r[0]: (r[1], r[2]) for r in report_manager.get_dish_rating()}
        self.assertEqual(rating["Котлеты по-киевски"], (2, 900.0))
        self.assertEqual(rating["Гренки чесночные"], (2, 300.0))
        self.assertNotIn("Борщ", rating)
        self.assertNotIn("Кофе Капучино", rating)

    def test_rating_ignores_cancelled_orders(self):
        order_manager.cancel_order(3, "Администратор")
        names = [r[0] for r in report_manager.get_dish_rating()]
        self.assertNotIn("Морс ягодный", names)
        self.assertNotIn("Стейк из судака", names)

    def test_rating_empty_when_no_orders(self):
        self.execute("DELETE FROM orders")
        self.assertEqual(report_manager.get_dish_rating(), [])

    def test_revenue_for_single_date(self):
        self.assertEqual(report_manager.get_revenue("01.10.2026"), (1, 700.0))

    def test_revenue_counts_only_paid_orders(self):
        self.assertEqual(report_manager.get_revenue("07.10.2026"), (0, 0))
        self.assertEqual(report_manager.get_revenue("01.10.2026", "31.10.2026"), (1, 700.0))

    def test_revenue_grows_after_payment(self):
        self.set_status(2, SERVED)
        order_manager.update_order_status(2, PAID, "Официант")
        self.assertEqual(report_manager.get_revenue("07.10.2026", "07.10.2026"), (1, 1250.0))
        self.assertEqual(report_manager.get_revenue("01.10.2026", "07.10.2026"), (2, 1950.0))

    def test_revenue_excludes_cancelled_and_unpaid(self):
        order_manager.cancel_order(3, "Администратор")
        self.assertEqual(report_manager.get_revenue("01.10.2026", "31.12.2026"), (1, 700.0))

    def test_revenue_period_boundaries_inclusive(self):
        self.assertEqual(report_manager.get_revenue("30.09.2026", "01.10.2026"), (1, 700.0))
        self.assertEqual(report_manager.get_revenue("01.10.2026", "01.10.2026"), (1, 700.0))
        self.assertEqual(report_manager.get_revenue("02.10.2026", "30.10.2026"), (0, 0))

    def test_revenue_start_after_end_rejected(self):
        with self.assertRaises(ValueError):
            report_manager.get_revenue("02.10.2026", "01.10.2026")

    def test_revenue_invalid_dates_rejected(self):
        for text in ("", None, "2026-10-01", "31.02.2026", "abc"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    report_manager.get_revenue(text)
        with self.assertRaises(ValueError):
            report_manager.get_revenue("01.10.2026", "bad")


    def test_employee_efficiency_counts_paid_orders_and_revenue(self):
        rows = report_manager.get_employee_efficiency()
        by_name = {name: (served, revenue) for name, served, revenue in rows}
        self.assertEqual(by_name["Иванов Иван Иванович"], (1, 700.0))
        self.assertEqual(by_name["Петрова Анна Сергеевна"], (0, 0.0))

    def test_employee_efficiency_date_filter(self):
        self.set_status(2, PAID)
        rows = report_manager.get_employee_efficiency("07.10.2026", "07.10.2026")
        by_name = {name: (served, revenue) for name, served, revenue in rows}
        self.assertEqual(by_name["Петрова Анна Сергеевна"], (1, 1250.0))
        self.assertEqual(by_name["Иванов Иван Иванович"], (0, 0.0))

    def test_cancelled_orders_include_potential_total(self):
        self.set_status(3, CANCELLED)
        rows = report_manager.get_cancelled_orders()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 3)
        self.assertEqual(rows[0][2], 12)
        self.assertEqual(rows[0][3], "Иванов Иван Иванович")
        self.assertEqual(rows[0][4], 1250.0)

    def test_cancelled_orders_empty_when_none_cancelled(self):
        self.assertEqual(report_manager.get_cancelled_orders(), [])


class TestEmployees(BaseDbTest):
    """ФТ-18, таблицы 1 и 2."""

    def test_list_and_get(self):
        self.assertEqual(len(user_manager.get_all_users()), 5)
        self.assertEqual(user_manager.get_user_by_id(5), (5, "Смирнова Елена Николаевна", "Администратор"))
        self.assertIsNone(user_manager.get_user_by_id(99))

    def test_insert_valid_positions(self):
        for pos in user_manager.get_valid_positions():
            with self.subTest(pos=pos):
                self.assertTrue(user_manager.insert_user("Новый Сотрудник", pos))

    def test_insert_invalid_position_or_empty_name_rejected(self):
        for name, pos in (("Имя", "Директор"), ("Имя", ""), ("Имя", None), ("", "Повар"), ("  ", "Повар"), (None, "Повар")):
            with self.subTest(name=name, pos=pos):
                with self.assertRaises(ValueError):
                    user_manager.insert_user(name, pos)
        self.assertEqual(self.count("employees"), 5)

    def test_update_user(self):
        user_manager.update_user(4, "Кузнецов Д. В.", "Повар")
        self.assertEqual(user_manager.get_user_by_id(4), (4, "Кузнецов Д. В.", "Повар"))

    def test_update_user_invalid_rejected(self):
        with self.assertRaises(ValueError):
            user_manager.update_user(4, "", "Повар")
        with self.assertRaises(ValueError):
            user_manager.update_user(4, "Имя", "Директор")
        with self.assertRaises(ValueError):
            user_manager.update_user(99, "Имя", "Повар")

    def test_delete_unused_user(self):
        uid = user_manager.insert_user("Временный", "Повар")
        user_manager.delete_user_by_id(uid)
        self.assertIsNone(user_manager.get_user_by_id(uid))

    def test_delete_user_with_orders_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            user_manager.delete_user_by_id(1)
        self.assertIsNotNone(user_manager.get_user_by_id(1))

    def test_delete_missing_user_rejected(self):
        with self.assertRaises(ValueError):
            user_manager.delete_user_by_id(99)


class TestRolesAndLogin(BaseDbTest):
    """Таблицы 1 и 2: роли и права, вход по ID."""

    def test_admin_has_all_functions(self):
        perms = login.get_role_permissions("Администратор")
        for needed in ("Вести меню и категории", "Вести сотрудников", "Получить отчёты (выручка)", "Оформить заказ"):
            self.assertIn(needed, perms)

    def test_waiter_permissions(self):
        perms = login.get_role_permissions("Официант")
        self.assertIn("Оформить заказ", perms)
        self.assertIn("Изменить состав заказа", perms)
        self.assertNotIn("Вести меню и категории", perms)
        self.assertNotIn("Вести сотрудников", perms)
        self.assertNotIn("Получить отчёты (выручка)", perms)

    def test_kitchen_permissions(self):
        for role in ("Повар", "Бармен"):
            perms = login.get_role_permissions(role)
            with self.subTest(role=role):
                self.assertIn("Изменить статус заказа", perms)
                self.assertIn("Просмотреть меню", perms)
                self.assertNotIn("Оформить заказ", perms)
                self.assertNotIn("Изменить состав заказа", perms)
                self.assertNotIn("Получить отчёты (выручка)", perms)

    def test_unknown_role_has_no_permissions(self):
        self.assertEqual(login.get_role_permissions("Гость"), [])
        self.assertEqual(login.get_role_permissions(None), [])

    def test_every_valid_position_has_permissions(self):
        for pos in user_manager.get_valid_positions():
            self.assertTrue(login.get_role_permissions(pos))

    def _login(self, typed):
        buf = io.StringIO()
        with mock.patch("builtins.input", return_value=typed), redirect_stdout(buf):
            result = login.login_ui()
        return result, buf.getvalue()

    def test_login_success(self):
        user, out = self._login("5")
        self.assertEqual(user, (5, "Смирнова Елена Николаевна", "Администратор"))
        self.assertIn("Успешный вход", out)

    def test_login_with_spaces(self):
        user, _ = self._login("  1 ")
        self.assertEqual(user[0], 1)

    def test_login_invalid_input_does_not_crash(self):
        for typed in ("abc", "", "  ", "-1", "1.5", "²", "١"):
            with self.subTest(typed=typed):
                user, out = self._login(typed)
                self.assertIsNone(user)
                self.assertIn("Ошибка", out)

    def test_login_unknown_id(self):
        user, out = self._login("999")
        self.assertIsNone(user)
        self.assertIn("не найден", out)

    def test_login_lookup(self):
        self.assertEqual(login.get_user_by_id(3)[2], "Повар")
        self.assertIsNone(login.get_user_by_id(0))


class TestAvailabilityAndConnection(BaseDbTest):
    """НФТ-6, НФТ-7."""

    def test_unavailable_dish_stays_in_old_orders(self):
        menu_manager.set_dish_availability(1, False)
        self.assertEqual(len(order_manager.get_order_items_details(1)), 2)
        with self.assertRaises(sqlite3.IntegrityError):
            order_manager.create_order(1, WAITER, [(1, 1)])

    def test_russian_text_roundtrip(self):
        did = menu_manager.insert_dish("Ёжик в тумане «особый»", "Съедобный ёж — №1", 99.9, 5)
        self.assertEqual(menu_manager.get_dish_by_id(did)[:2], ("Ёжик в тумане «особый»", "Съедобный ёж — №1"))

    def test_missing_database_gives_database_error(self):
        order_manager.DB_PATH = Path(self._tmp.name) / "missing_dir" / "none.db"
        with self.assertRaises(sqlite3.Error):
            order_manager.get_statuses()

    def test_foreign_keys_enabled_in_every_connection(self):
        for module in (menu_manager, order_manager, user_manager, login):
            with self.subTest(module=module.__name__):
                conn = module.get_connection()
                try:
                    self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
