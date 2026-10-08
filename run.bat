@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo [ИНФО]: Виртуальное окружение не найдено. Создание .venv...
    python -m venv .venv
    call .venv\Scripts\activate
    echo [ИНФО]: Установка зависимостей...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install pyinstaller
)

if not exist "CapyCafe\CapyCafe.exe" (
    echo [ИНФО]: Сборка исполняемого файла CapyCafe.exe...
    .venv\Scripts\python.exe -m PyInstaller --onedir --console --name CapyCafe --distpath . main\main.py
    
    :: Чистим временный мусор компилятора, чтобы не занимал место
    rmdir /s /q build
    del /q CapyCafe.spec
)

cls
if exist "CapyCafe\CapyCafe.exe" (
    cd CapyCafe
    CapyCafe.exe
) else (
    echo [КРИТИЧЕСКАЯ ОШИБКА]: Не удалось собрать исполняемый файл.
    pause
)
