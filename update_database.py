#!/usr/bin/env python3
"""
Скрипт для обновления базы данных с новыми полями для AI улучшения сплетен
"""

import os
import sys
from sqlalchemy import text

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def update_database():
    """Обновляет базу данных, добавляя новые поля для AI улучшения"""
    
    # Создаем контекст приложения
    ctx = app.app_context()
    ctx.push()
    
    try:
        # Проверяем, существуют ли уже новые поля
        result = db.session.execute(text("""
            SELECT name FROM pragma_table_info('gossip') 
            WHERE name IN ('is_ai_enhanced', 'ai_enhanced_at')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        print("Существующие поля:", existing_columns)
        
        # Добавляем поле is_ai_enhanced если его нет
        if 'is_ai_enhanced' not in existing_columns:
            print("Добавляем поле is_ai_enhanced...")
            db.session.execute(text("""
                ALTER TABLE gossip 
                ADD COLUMN is_ai_enhanced BOOLEAN DEFAULT FALSE
            """))
            print("✓ Поле is_ai_enhanced добавлено")
        
        # Добавляем поле ai_enhanced_at если его нет
        if 'ai_enhanced_at' not in existing_columns:
            print("Добавляем поле ai_enhanced_at...")
            db.session.execute(text("""
                ALTER TABLE gossip 
                ADD COLUMN ai_enhanced_at DATETIME
            """))
            print("✓ Поле ai_enhanced_at добавлено")
        
        # Сохраняем изменения
        db.session.commit()
        print("✓ База данных успешно обновлена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")
        db.session.rollback()
        return False
    finally:
        ctx.pop()

if __name__ == "__main__":
    print("Обновление базы данных для поддержки AI улучшения сплетен...")
    if update_database():
        print("Обновление завершено успешно!")
    else:
        print("Обновление не удалось!")
        sys.exit(1)
