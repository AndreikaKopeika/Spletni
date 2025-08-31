#!/usr/bin/env python3
"""
Скрипт для обновления базы данных в Docker
Добавляет необходимые поля для AI улучшения сплетен
"""

import sqlite3
import os
import sys

def update_database():
    """Обновляет базу данных, добавляя новые поля"""
    db_path = 'instance/gossip.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        print("Создаем новую базу данных...")
        return True
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли поле has_used_free_enhancement
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'has_used_free_enhancement' not in columns:
            print("Добавляем поле has_used_free_enhancement в таблицу user...")
            cursor.execute("ALTER TABLE user ADD COLUMN has_used_free_enhancement BOOLEAN DEFAULT FALSE")
            conn.commit()
            print("✅ Поле has_used_free_enhancement успешно добавлено!")
        else:
            print("✅ Поле has_used_free_enhancement уже существует")
        
        # Проверяем, существует ли поле is_ai_enhanced в таблице gossip
        cursor.execute("PRAGMA table_info(gossip)")
        gossip_columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_ai_enhanced' not in gossip_columns:
            print("Добавляем поле is_ai_enhanced в таблицу gossip...")
            cursor.execute("ALTER TABLE gossip ADD COLUMN is_ai_enhanced BOOLEAN DEFAULT FALSE")
            conn.commit()
            print("✅ Поле is_ai_enhanced успешно добавлено!")
        else:
            print("✅ Поле is_ai_enhanced уже существует")
        
        # Проверяем, существует ли поле ai_enhanced_at в таблице gossip
        if 'ai_enhanced_at' not in gossip_columns:
            print("Добавляем поле ai_enhanced_at в таблицу gossip...")
            cursor.execute("ALTER TABLE gossip ADD COLUMN ai_enhanced_at DATETIME")
            conn.commit()
            print("✅ Поле ai_enhanced_at успешно добавлено!")
        else:
            print("✅ Поле ai_enhanced_at уже существует")
        
        # Показываем структуру таблиц
        print("\n📊 Структура таблицы user:")
        cursor.execute("PRAGMA table_info(user)")
        for column in cursor.fetchall():
            print(f"  - {column[1]} ({column[2]})")
        
        print("\n📊 Структура таблицы gossip:")
        cursor.execute("PRAGMA table_info(gossip)")
        for column in cursor.fetchall():
            print(f"  - {column[1]} ({column[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Обновление базы данных для AI улучшения сплетен...")
    if update_database():
        print("✅ Обновление завершено успешно!")
        sys.exit(0)
    else:
        print("❌ Обновление не удалось!")
        sys.exit(1)
