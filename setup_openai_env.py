#!/usr/bin/env python3
"""
Скрипт для установки переменной окружения OPENAI_API_KEY
"""

import os
import sys
import platform
import subprocess
from dotenv import load_dotenv

def setup_openai_environment():
    """Устанавливает переменную окружения OPENAI_API_KEY"""
    
    # Загружаем .env файл
    load_dotenv()
    
    # Получаем API ключ из .env
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key or api_key == 'NEW_OPENAI_API_KEY_HERE_REPLACE_THIS':
        print("❌ OPENAI_API_KEY не найден в .env файле или не настроен")
        print("Пожалуйста, добавьте ваш API ключ в .env файл:")
        print("OPENAI_API_KEY=sk-your_actual_api_key_here")
        return False
    
    try:
        if platform.system() == "Windows":
            # Для Windows используем setx
            print("🪟 Устанавливаем переменную окружения в Windows...")
            result = subprocess.run(['setx', 'OPENAI_API_KEY', api_key], 
                                  capture_output=True, text=True, check=True)
            print("✅ Переменная окружения установлена в Windows")
            print("💡 Перезапустите командную строку для применения изменений")
            
        else:
            # Для Linux/Mac
            print("🐧 Устанавливаем переменную окружения в Linux/Mac...")
            
            home = os.path.expanduser("~")
            bashrc_path = os.path.join(home, ".bashrc")
            profile_path = os.path.join(home, ".profile")
            
            export_line = f'export OPENAI_API_KEY="{api_key}"\n'
            
            # Добавляем в .bashrc
            if os.path.exists(bashrc_path):
                with open(bashrc_path, 'a') as f:
                    f.write(export_line)
                print(f"✅ Добавлено в {bashrc_path}")
            
            # Добавляем в .profile
            with open(profile_path, 'a') as f:
                f.write(export_line)
            print(f"✅ Добавлено в {profile_path}")
            
            # Устанавливаем для текущей сессии
            os.environ['OPENAI_API_KEY'] = api_key
            print("✅ Переменная установлена для текущей сессии")
            print("💡 Выполните 'source ~/.bashrc' или перезапустите терминал")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при установке переменной окружения: {e}")
        print(f"Вывод: {e.stdout}")
        print(f"Ошибка: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_openai_connection():
    """Тестирует подключение к OpenAI API"""
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY не найден в переменных окружения")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Простой тест API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Привет! Это тест."}],
            max_tokens=10
        )
        
        print("✅ Подключение к OpenAI API успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к OpenAI API: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Настройка переменной окружения OPENAI_API_KEY")
    print("=" * 50)
    
    if setup_openai_environment():
        print("\n🧪 Тестирование подключения к OpenAI API...")
        if test_openai_connection():
            print("\n🎉 Все готово! OpenAI API настроен и работает.")
        else:
            print("\n⚠️ Переменная окружения установлена, но есть проблемы с API ключом.")
    else:
        print("\n❌ Не удалось настроить переменную окружения.")
        sys.exit(1)
