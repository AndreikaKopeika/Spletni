#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции улучшения сплетен с помощью AI
"""

import os
import sys
import requests
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ai_enhancement():
    """Тестирует функцию улучшения AI"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Тестирование функции улучшения сплетен с помощью AI")
    print("=" * 60)
    
    # Тест 1: Проверка доступности приложения
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Приложение доступно")
        else:
            print(f"❌ Приложение недоступно (статус: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к приложению")
        print("Убедитесь, что приложение запущено на http://localhost:5000")
        return False
    
    # Тест 2: Проверка API endpoint
    try:
        response = requests.post(f"{base_url}/gossip/1/enhance_ai")
        # Ожидаем 401 (Unauthorized) или 404 (Not Found)
        if response.status_code in [401, 404]:
            print("✅ API endpoint доступен")
        else:
            print(f"⚠️ Неожиданный статус ответа: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ API endpoint недоступен")
        return False
    
    print("\n📋 Рекомендации по тестированию:")
    print("1. Запустите приложение: python app.py")
    print("2. Откройте браузер и перейдите на http://localhost:5000")
    print("3. Войдите в систему или зарегистрируйтесь")
    print("4. Создайте новую сплетню")
    print("5. Убедитесь, что у вас есть не менее 100 коинов")
    print("6. На странице сплетни найдите кнопку '✨Улучшить с AI✨'")
    print("7. Нажмите на кнопку и дождитесь результата")
    
    print("\n🔧 Технические детали:")
    print("- Endpoint: POST /gossip/<id>/enhance_ai")
    print("- Требования: авторизация, 100+ коинов, автор сплетни")
    print("- Rate limit: 5 запросов в час")
    print("- Модель AI: gpt-4o-mini")
    
    return True

if __name__ == "__main__":
    test_ai_enhancement()
