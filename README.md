# Этап 4. Проектирование и реализация базы данных

На данном этапе выполнено проектирование и техническая реализация локальной реляционной базы данных информационной системы кафе «Причал» на базе СУБД **SQLite**. База данных интегрирована непосредственно в репозиторий проекта в виде переносимого файла данных **`capycafe.db`**.

---

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
| **dishes** | `is_available` | INTEGER | NOT NULL, DEFAULT 1 (1-в наличии, 0-стоп) |
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
| **order_items** | `quantity` | INTEGER | NOT NULL, `CHECK (quantity > 0)` (Количество) |
| **order_items** | `price_at_order` | REAL | NOT NULL, `CHECK (price_at_order > 0)` (Цена фиксации) |

### Характер и типы связей (Инфологическая модель)
* `categories` ➔ `dishes` (**1:N**): Одна категория содержит множество блюд.
* `employees` ➔ `orders` (**1:N**): Один официант может принять множество заказов.
* `order_statuses` ➔ `orders` (**1:N**): Один статус применяется ко многим заказам.
* `orders` ➔ `order_items` (**1:N**): Один чек содержит одну или несколько позиций блюд. При удалении заказа его позиции каскадно очищаются (`ON DELETE CASCADE`).
* `dishes` ➔ `order_items` (**1:N**): Одно блюдо может фигурировать в составе разных чеков, что организует реляционную связь **M:N (Многие-ко-Многим)** между Заказами и Меню. Для исключения дублирования строк наложен композитный индекс `UNIQUE(order_id, dish_id)`.

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

```sql
INSERT OR IGNORE INTO categories (name) VALUES 
('Закуски'), ('Салаты'), ('Супы'), ('Горячие блюда'), ('Десерты'), ('Напитки');

INSERT OR IGNORE INTO employees (full_name, position) VALUES 
('Иванов Иван Иванович', 'Официант'), ('Петрова Анна Сергеевна', 'Официант'),
('Сидоров Алексей Петрович', 'Повар'), ('Кузнецов Дмитрий Владимирович', 'Бармен'),
('Смирнова Елена Николаевна', 'Администратор');

INSERT OR IGNORE INTO order_statuses (name) VALUES 
('Принят'), ('Готовится'), ('Готов'), ('Выдан'), ('Оплачен'), ('Отменён');

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

INSERT OR IGNORE INTO orders (order_date, table_number, employee_id, status_id) VALUES 
('2026-10-01 13:15:00', 3, 1, 5),
('2026-10-02 12:00:00', 5, 2, 2),
('2026-10-02 12:30:00', 12, 1, 5);

INSERT OR IGNORE INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES 
(1, 1, 2, 150.00), (1, 3, 1, 400.00),
(2, 2, 1, 350.00), (2, 6, 2, 450.00),
(3, 5, 1, 550.00), (3, 7, 2, 250.00), (3, 8, 3, 100.00);
```

---

## 4. Сценарии тестирования и верификации БД (Тест-кейсы)

Инструкции предназначены для проверки работоспособности ограничений целостности и выполнения аналитических выборок.

### Тест-кейс 1: Проверка ограничений CHECK (Ожидается аппаратная ошибка СУБД)
```sql
-- А. Попытка установить отрицательную цену (Ошибка chk_dish_price)
INSERT INTO dishes (name, price, category_id) VALUES ('Невалидный суп', -50.00, 3);

-- Б. Номер стола вне диапазона 1-12 (Ошибка chk_table_number)
INSERT INTO orders (table_number, employee_id, status_id) VALUES (25, 1, 1);

-- В. Отрицательный объем порций (Ошибка chk_item_quantity)
INSERT INTO order_items (order_id, dish_id, quantity, price_at_order) VALUES (1, 1, -5, 150.00);
```

### Тест-кейс 2: Фильтрация меню и поиск доступных блюд
```sql
SELECT d.id, d.name, d.price, c.name AS category_name 
FROM dishes d
JOIN categories c ON d.category_id = c.id
WHERE d.is_available = 1 
  AND d.category_id = 3
  AND d.name LIKE '%Уха%'
ORDER BY d.price ASC;
```

### Тест-кейс 3: Мониторинг заказов с автоматическим подсчетом суммы чека
```sql
SELECT 
    o.id AS order_number, o.order_date, o.table_number,
    e.full_name AS waiter, s.name AS status,
    COALESCE(SUM(oi.quantity * oi.price_at_order), 0) AS total_price
FROM orders o
JOIN employees e ON o.employee_id = e.id
JOIN order_statuses s ON o.status_id = s.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id
ORDER BY o.order_date DESC;
```

### Тест-кейс 4: Аналитика популярности меню (Рейтинг продаж)
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

## 6. Техническое окружение и переносимость БД
Для обеспечения изоляции проекта и его гарантированного запуска на любом рабочем месте развернута следующая инфраструктура:
1. **Виртуальное окружение**: Инициализировано изолированное окружение в каталоге `.venv/`.
2. **Файл конфигурации зависимостей**: Создан стандартный реестр компонентов `requirements.txt`.
3. **Физический файл данных**: Готовая реляционная база данных со структурой и тестовыми строками зафиксирована непосредственно в репозитории по пути: `database/capycafe.db`. 

Развертывание и верификация базы данных **Этапа 4 успешно завершены**. Локальный файл базы данных полностью автономен, защищен правилами `.gitignore` от системных транзакционных блокировок и готов к программному подключению.
