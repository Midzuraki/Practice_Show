import tempfile
import unittest
from pathlib import Path

from database.scripts.dishes import menu_manager
from database.scripts.orders import order_manager
from database.scripts.reports import report_manager
from database.scripts.authorization import user_manager


class ReportAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        with __import__("sqlite3").connect(self.db_path) as conn:
            conn.executescript(Path("database/schema.sql").read_text(encoding="utf-8"))
            conn.executescript(Path("database/data.sql").read_text(encoding="utf-8"))
        self.modules = (menu_manager, order_manager, report_manager, user_manager)
        self.old_paths = [module.DB_PATH for module in self.modules]
        for module in self.modules:
            module.DB_PATH = self.db_path

    def tearDown(self):
        for module, old_path in zip(self.modules, self.old_paths):
            module.DB_PATH = old_path
        self.temp_dir.cleanup()

    def test_rating_excludes_cancelled_orders_but_includes_open_orders(self):
        order_manager.update_order_status(3, order_manager.STATUS_CANCELLED)
        rows = report_manager.get_dish_rating()
        names = {row[0] for row in rows}
        self.assertIn("Гренки чесночные", names)
        self.assertIn("Салат Цезарь", names)
        self.assertNotIn("Стейк из судака", names)

    def test_category_crud_is_available_in_data_layer(self):
        category_id = menu_manager.add_category("Тестовая категория")
        menu_manager.rename_category(category_id, "Новая категория")
        self.assertIn((category_id, "Новая категория"), menu_manager.get_categories())
        menu_manager.delete_category(category_id)
        self.assertNotIn(category_id, {row[0] for row in menu_manager.get_categories()})

    def test_status_transition_rules_remain_enforced(self):
        order_manager.update_order_status(2, order_manager.STATUS_READY)
        with self.assertRaises(ValueError):
            order_manager.update_order_status(2, order_manager.STATUS_ACCEPTED)


    def test_active_orders_include_total_amount(self):
        orders = order_manager.get_active_orders()
        order_two = next(row for row in orders if row[0] == 2)
        self.assertEqual(order_two[5], 1250.0)

    def test_role_cannot_set_another_department_status(self):
        with self.assertRaises(ValueError):
            order_manager.update_order_status(2, order_manager.STATUS_READY, role="Официант")
        info = order_manager.get_order_info(2)
        self.assertEqual(info[4], "Готовится")

    def test_only_waiter_or_admin_can_create_order(self):
        with self.assertRaises(ValueError):
            order_manager.create_order(4, 3, [(1, 1)])

    def test_revenue_counts_paid_orders_only(self):
        count, total = report_manager.get_revenue("01.10.2026")
        self.assertEqual(count, 1)
        self.assertEqual(total, 700.0)


if __name__ == "__main__":
    unittest.main()
