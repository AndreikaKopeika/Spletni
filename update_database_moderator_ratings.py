#!/usr/bin/env python3
"""
Скрипт для безопасного обновления базы данных
Добавляет таблицу moderator_rating для оценок сплетен модераторами
"""

import sqlite3
import os
from datetime import datetime

def update_database():
    """Безопасно обновляет базу данных"""
    db_path = 'instance/gossip.db'
    
    if not os.path.exists(db_path):
        print("База данных не найдена!")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Проверяем существование таблицы moderator_rating...")
        
        # Проверяем, существует ли уже таблица
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='moderator_rating'
        """)
        
        if cursor.fetchone():
            print("Таблица moderator_rating уже существует!")
            conn.close()
            return True
        
        print("Создаем таблицу moderator_rating...")
        
        # Создаем таблицу moderator_rating
        cursor.execute("""
            CREATE TABLE moderator_rating (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moderator_id INTEGER NOT NULL,
                gossip_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                rated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (moderator_id) REFERENCES user (id),
                FOREIGN KEY (gossip_id) REFERENCES gossip (id)
            )
        """)
        
        # Создаем индексы для оптимизации
        cursor.execute("""
            CREATE INDEX idx_moderator_rating_moderator_id 
            ON moderator_rating (moderator_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_moderator_rating_gossip_id 
            ON moderator_rating (gossip_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_moderator_rating_rated_at 
            ON moderator_rating (rated_at)
        """)
        
        # Создаем уникальный индекс для предотвращения дублирования оценок
        cursor.execute("""
            CREATE UNIQUE INDEX idx_moderator_rating_unique 
            ON moderator_rating (moderator_id, gossip_id)
        """)
        
        # Сохраняем изменения
        conn.commit()
        conn.close()
        
        print("✅ Таблица moderator_rating успешно создана!")
        print("✅ Индексы созданы для оптимизации запросов")
        print("✅ Уникальный индекс создан для предотвращения дублирования")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=== Обновление базы данных для системы оценок модераторов ===")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = update_database()
    
    if success:
        print("\n🎉 Обновление базы данных завершено успешно!")
        print("Теперь модераторы могут оценивать сплетни от 1 до 10 баллов.")
    else:
        print("\n💥 Обновление базы данных завершилось с ошибкой!")
        print("Проверьте логи выше для получения дополнительной информации.")
