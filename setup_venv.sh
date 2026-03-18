#!/usr/bin/env bash
# Скрипт создания виртуального окружения для Flashscore Parser

set -e

echo "=== Создание виртуального окружения ==="
python3 -m venv venv

echo "=== Активация ==="
source venv/bin/activate

echo "=== Установка зависимостей ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Установка браузера Chromium для Playwright ==="
playwright install chromium

echo ""
echo "✅ Готово! Для запуска парсера:"
echo ""
echo "   source venv/bin/activate"
echo "   python flashscore_full_parser.py"
echo ""
echo "Для Windows используй: venv\\Scripts\\activate"
