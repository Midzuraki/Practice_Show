-- ==========================================
-- Скрипт создания базы данных "Кафе Причал"
-- СУБД: SQLite (База данных в одном файле)
-- ==========================================

-- Включаем поддержку внешних ключей в SQLite (обязательно выполнять при каждом подключении)
PRAGMA foreign_keys = ON;

-- 1. Таблица "Категории меню"
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- 2. Таблица "Сотрудники"
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    position TEXT NOT NULL
);

-- 3. Таблица "Статусы заказов"
CREATE TABLE IF NOT EXISTS order_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- 4. Таблица "Блюда"
CREATE TABLE IF NOT EXISTS dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1, -- 1 = TRUE, 0 = FALSE
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    CONSTRAINT chk_dish_price CHECK (price > 0)
);

-- 5. Таблица "Заказы"
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    table_number INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY (status_id) REFERENCES order_statuses(id) ON DELETE RESTRICT,
    CONSTRAINT chk_table_number CHECK (table_number BETWEEN 1 AND 12)
);

-- 6. Таблица "Позиции заказа" (Состав заказа)
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    dish_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_at_order REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE RESTRICT,
    CONSTRAINT chk_item_quantity CHECK (quantity > 0),
    CONSTRAINT chk_item_price CHECK (price_at_order > 0),
    UNIQUE(order_id, dish_id) -- Предотвращает дублирование одного блюда в одном чеке
);

-- ==========================================
-- Заполнение таблиц тестовыми данными
-- ==========================================

-- Категории
INSERT OR IGNORE INTO categories (name) VALUES
('Закуски'), ('Салаты'), ('Супы'), ('Горячие блюда'), ('Десерты'), ('Напитки');

-- Сотрудники
INSERT OR IGNORE INTO employees (full_name, position) VALUES
('Иванов Иван Иванович', 'Официант'),
('Петрова Анна Сергеевна', 'Официант'),
('Сидоров Алексей Петрович', 'Повар'),
('Кузнецов Дмитрий Владимирович', 'Бармен'),
('Смирнова Елена Николаевна', 'Администратор');

-- Статусы
INSERT OR IGNORE INTO order_statuses (name) VALUES
('Принят'), ('Готовится'), ('Готов'), ('Выдан'), ('Оплачен'), ('Отменён');

-- Блюда
INSERT OR IGNORE INTO dishes (name, description, price, is_available, category_id) VALUES
('Гренки чесночные', 'Ржаные гренки с чесночным соусом', 150.00, 1, 1),
('Салат Цезарь', 'Классический салат с курицей', 350.00, 1, 2),
('Уха Астраханская', 'Традиционный суп из местной рыбы', 400.00, 1, 3),
('Борщ', 'Классический мясной борщ со сметаной', 300.00, 1, 3),
('Стейк из судака', 'Судак на гриле с овощами', 550.00, 1, 4),
('Котлеты по-киевски', 'С картофельным пюре', 450.00, 1, 4),
('Торт Наполеон', 'Домашний слоеный торт', 250.00, 1, 5),
('Морс ягодный', 'Собственного приготовления', 100.00, 1, 6),
('Кофе Капучино', 'Классический кофейный напиток', 180.00, 0, 6);

-- Заказы
INSERT OR IGNORE INTO orders (order_date, table_number, employee_id, status_id) VALUES
('2026-10-01 13:15:00', 3, 1, 5),
('2026-10-02 12:00:00', 5, 2, 2),
('2026-10-02 12:30:00', 12, 1, 5);

-- Состав заказов
INSERT OR IGNORE INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES
(1, 1, 2, 150.00),
(1, 3, 1, 400.00),
(2, 2, 1, 350.00),
(2, 6, 2, 450.00),
(3, 5, 1, 550.00),
(3, 7, 2, 250.00),
(3, 8, 3, 100.00);
