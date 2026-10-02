# Этап 4. Проектирование и реализация базы данных

На данном этапе выполнено проектирование и техническая реализация локальной реляционной базы данных информационной системы кафе «Причал» на базе СУБД **SQLite**. База данных интегрирована непосредственно в репозиторий проекта в виде переносимого файла данных **`capycafe.db`**.

---

## 1. Определение сущностей, атрибутов и ограничений целостности

На основе системных требований предметной области выделено **6 взаимосвязанных таблиц**. Для обеспечения ссылочной целостности на уровне ядра СУБД активирован режим поддержки внешних ключей (`PRAGMA foreign_keys = ON`), а также добавлены ограничения `CHECK` и `UNIQUE`.

## 1. Определение сущностей, атрибутов и ограничений целостности

На основе системных требований предметной области выделено **6 взаимосвязанных таблиц**. Для обеспечения ссылочной целостности на уровне ядра СУБД активирован режим поддержки внешних ключей (`PRAGMA foreign_keys = ON`), а также добавлены ограничения `CHECK` и `UNIQUE`.

### Структура и состав таблиц

| Таблица | Поле (Атрибут) | Тип данных | Описание / Ограничения |
| :--- | :--- | :--- | :--- |
| **categories** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **categories** | `name` | TEXT | UNIQUE, NOT NULL (Название категории) |
| **dishes** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **dishes** | `name` | TEXT | NOT NULL (Название блюда) |
| **dishes** | `description` | TEXT | NULL (Описание ингредиентов) |
| **dishes** | `price` | REAL | NOT NULL, `CHECK (price > 0)` (Цена) |
| **dishes** | `is_available` | INTEGER | NOT NULL, DEFAULT 1 (1 — в наличии, 0 — стоп-лист) |
| **dishes** | `category_id` | INTEGER | FOREIGN KEY -> `categories(id)` ON DELETE RESTRICT |
| **employees** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **employees** | `full_name` | TEXT | NOT NULL (ФИО сотрудника) |
| **employees** | `position` | TEXT | NOT NULL (Должность: официант/повар/админ) |
| **order_statuses** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **order_statuses** | `name` | TEXT | UNIQUE, NOT NULL (Название статуса заказа) |
| **orders** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **orders** | `order_date` | TEXT | NOT NULL, DEFAULT (текущее локальное время) |
| **orders** | `table_number` | INTEGER | NOT NULL, `CHECK (table_number BETWEEN 1 AND 12)` |
| **orders** | `employee_id` | INTEGER | FOREIGN KEY -> `employees(id)` ON DELETE RESTRICT |
| **orders** | `status_id` | INTEGER | FOREIGN KEY -> `order_statuses(id)` ON DELETE RESTRICT |
| **order_items** | `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| **order_items** | `order_id` | INTEGER | FOREIGN KEY -> `orders(id)` ON DELETE CASCADE |
| **order_items** | `dish_id` | INTEGER | FOREIGN KEY -> `dishes(id)` ON DELETE RESTRICT |
| **order_items** | `quantity` | INTEGER | NOT NULL, `CHECK (quantity > 0)` (Количество порций) |
| **order_items** | `price_at_order` | REAL | NOT NULL, `CHECK (price_at_order > 0)` (Цена продажи) |

---

## 2. SQL-скрипт создания структуры базы данных (DDL)

Скрипт формирует каркас базы данных и накладывает правила валидации данных на уровне таблиц.

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    position TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    CONSTRAINT chk_dish_price CHECK (price > 0)
);

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
    UNIQUE(order_id, dish_id)
);
```

---

## 3. SQL-скрипт заполнения тестовыми данными (DML)

Скрипт вносит демонстрационные данные для симуляции реального рабочего дня кафе:

```sql
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
```

---

## 4. Разработка SQL-запросов для обработки и получения данных

Данные выборки предназначены для интеграции в C#-приложение для реализации функций поиска и аналитической отчетности администрации кафе.

### 4.1 Фильтрация и поиск доступных блюд
```sql
SELECT d.id, d.name, d.price, c.name AS category_name 
FROM dishes d
JOIN categories c ON d.category_id = c.id
WHERE d.is_available = 1 
  AND d.category_id = 3
  AND d.name LIKE '%Уха%'
ORDER BY d.price ASC;
```

### 4.2 Просмотр активных заказов с расчетом суммы чека
```sql
SELECT 
    o.id AS order_number,
    o.order_date,
    o.table_number,
    e.full_name AS waiter,
    s.name AS status,
    COALESCE(SUM(oi.quantity * oi.price_at_order), 0) AS total_price
FROM orders o
JOIN employees e ON o.employee_id = e.id
JOIN order_statuses s ON o.status_id = s.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id
ORDER BY o.order_date DESC;
```

### 4.3 Вывод детализации (состава) выбранного заказа
```sql
SELECT 
    d.name AS dish_name,
    oi.quantity,
    oi.price_at_order AS price_per_item,
    (oi.quantity * oi.price_at_order) AS item_total
FROM order_items oi
JOIN dishes d ON oi.dish_id = d.id
WHERE oi.order_id = 3;
```

### 4.4 Аналитический отчет: Рейтинг популярности блюд
```sql
SELECT 
    d.name AS dish_name,
    SUM(oi.quantity) AS total_portions_sold,
    SUM(oi.quantity * oi.price_at_order) AS total_revenue
FROM order_items oi
JOIN dishes d ON oi.dish_id = d.id
JOIN orders o ON oi.order_id = o.id
WHERE o.status_id = 5 
GROUP BY d.id
ORDER BY total_portions_sold DESC;
```

---

## 5. Проверка корректности структуры и целостности данных
Успешное выполнение скрипта в среде разработки подтвердило:
1. Корректность генерации связей типа «Один-ко-многим».
2. Функционирование ограничений (`CHECK CONSTRAINTS`), блокирующих занесение некорректных цен или номеров столов вне лимита 1-12.
3. Работоспособность механизмов защиты `ON DELETE RESTRICT`, предотвращающих случайное удаление номенклатуры, связанной с историей архивных заказов.

Файл базы данных **`capycafe.db`** успешно сформирован и инициализирован в корневом каталоге проекта.
