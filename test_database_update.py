#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обновления базы данных
"""

import sqlite3
import os

def test_database_structure():
    """Проверяет структуру базы данных"""
    db_path = 'instance/gossip.db'
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем таблицу user
        print("📊 Проверка таблицы user:")
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        required_user_fields = [
            'id', 'username', 'password', 'date_registered', 
            'is_moderator', 'is_verified', 'is_bot', 'reputation', 
            'description', 'gossip_coins', 'pinned_gossip_id', 
            'active_decoration_id', 'notify_on_like', 'notify_on_comment', 
            'last_seen', 'has_used_free_enhancement'
        ]
        
        for field in required_user_fields:
            if field in user_columns:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - ОТСУТСТВУЕТ")
        
        # Проверяем таблицу gossip
        print("\n📊 Проверка таблицы gossip:")
        cursor.execute("PRAGMA table_info(gossip)")
        gossip_columns = [column[1] for column in cursor.fetchall()]
        
        required_gossip_fields = [
            'id', 'title', 'content', 'date_posted', 'user_id', 
            'likes', 'comments', 'is_pinned', 'is_ai_enhanced', 'ai_enhanced_at'
        ]
        
        for field in required_gossip_fields:
            if field in gossip_columns:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - ОТСУТСТВУЕТ")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Тестирование структуры базы данных...")
    test_database_structure()
    print("\n✅ Тестирование завершено!")
