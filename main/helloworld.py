from pathlib import Path
import subprocess
import sys


def find_file(filename):
    current = Path(__file__).resolve()

    for parent in (current.parent, *current.parents):
        for file in parent.rglob(filename):
            if file.is_file():
                return file

    raise FileNotFoundError(
        f"Не удалось найти файл: {filename}"
    )


def run_in_console():
    print("=" * 60)
    print("CAPYCAFE")
    print("=" * 60)

    insert_db = find_file("insert_db.py")

    print(f"\nНайден insert_db.py:")
    print(insert_db)

    print("\n" + "=" * 60)
    print("ЗАПУСК INSERT_DB.PY")
    print("=" * 60 + "\n")

    result = subprocess.run(
        [sys.executable, str(insert_db)],
        cwd=insert_db.parent
    )

    # Если insert_db.py завершился с ошибкой
    if result.returncode != 0:
        print("\n" + "=" * 60)
        print("ОШИБКА!")
        print(f"insert_db.py завершился с кодом: {result.returncode}")
        print("=" * 60)
        input("\nНажмите Enter для выхода...")
        return

    print("\n" + "=" * 60)
    print("БАЗА ДАННЫХ УСПЕШНО ОБРАБОТАНА")
    print("=" * 60)

    # Поиск menu_manager.py
    menu_manager = find_file("menu_manager.py")

    print(f"\nНайден menu_manager.py:")
    print(menu_manager)

    print("\n" + "=" * 60)
    print("ЗАПУСК MENU_MANAGER.PY")
    print("=" * 60 + "\n")

    result = subprocess.run(
        [sys.executable, str(menu_manager)],
        cwd=menu_manager.parent
    )

    print("\n" + "=" * 60)

    if result.returncode == 0:
        print("MENU_MANAGER ЗАВЕРШЁН УСПЕШНО")
    else:
        print(
            f"MENU_MANAGER ЗАВЕРШЁН С ОШИБКОЙ: "
            f"{result.returncode}"
        )

    print("=" * 60)

    input("\nНажмите Enter для выхода...")


def main():
    if "--console" not in sys.argv:

        subprocess.Popen(
            [
                "cmd.exe",
                "/k",
                sys.executable,
                str(Path(__file__).resolve()),
                "--console"
            ],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        return

    run_in_console()


if __name__ == "__main__":
    main()