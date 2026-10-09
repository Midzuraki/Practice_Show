# Папка tests

Здесь находятся дополнительные регрессионные тесты, дополняющие основной набор из `database/scripts/test/tests.py`.

Файл `test_report_alignment.py` проверяет согласованность расчётов отчётности, в частности исключение отменённых заказов из рейтинга блюд, и восстанавливает тестовые настройки пути к базе после выполнения.

Запуск из корня проекта:

```bash
python -m unittest tests.test_report_alignment
python -m unittest database.scripts.test.tests
```

Перед отправкой изменений также полезно проверить синтаксис:

```bash
python -m compileall -q main database tests
```
