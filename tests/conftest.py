import pytest
import os
import sys

# Добавляем корневую папку проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app, db, User, Quest, Decoration, bcrypt
from sqlalchemy.pool import StaticPool

# Устанавливаем переменные окружения для тестов
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DEVELOPER_PASSWORD'] = 'test-dev-password'

@pytest.fixture(scope='function')
def app():
    """Создаем тестовое приложение с изолированной базой данных для каждого теста."""
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:?cache=shared'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['SQLALCHEMY_EXPIRE_ON_COMMIT'] = False
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': StaticPool,
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30
        }
    }
    
    # Отключаем rate limiting в тестах
    flask_app.config['RATELIMIT_ENABLED'] = False
    
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        
        # Создаем базовые квесты и украшения
        if Quest.query.first() is None:
            quests = [
                Quest(name='Лайк за лайк', description='Поставьте 10 лайков.', quest_type='LIKE_GOSSIP', goal=10, reward=15),
                Quest(name='Комментатор', description='Оставьте 5 комментариев.', quest_type='POST_COMMENT', goal=5, reward=20),
                Quest(name='Начинающий писатель', description='Опубликуйте 2 сплетни.', quest_type='POST_GOSSIP', goal=2, reward=25),
                Quest(name='Популярность', description='Получите 15 лайков на свои сплетни.', quest_type='GET_LIKES', goal=15, reward=30),
            ]
            db.session.bulk_save_objects(quests)
            
        if Decoration.query.first() is None:
            decorations = [
                Decoration(name='Обычная рамка', description='Простая рамка', price=10, css_class='frame-common', rarity='common'),
                Decoration(name='Редкая рамка', description='Редкая рамка', price=50, css_class='frame-rare', rarity='rare'),
                Decoration(name='Модератор', description='Аура модератора', price=0, css_class='frame-moderator', rarity='legendary', is_purchasable=False),
                Decoration(name='Верификация', description='Свечение верификации', price=0, css_class='frame-verified', rarity='legendary', is_purchasable=False),
            ]
            db.session.bulk_save_objects(decorations)
            
        db.session.commit()
        
        yield flask_app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def new_user(app):
    """Создаем тестового пользователя."""
    with app.app_context():
        # Удаляем существующего пользователя если есть
        User.query.filter_by(username='testuser').delete()
        db.session.commit()
        
        # Создаем нового пользователя с хешированным паролем
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(username='testuser', password=hashed_password)
        user.gossip_coins = 100
        db.session.add(user)
        db.session.commit()
        
        yield user
        
        # Очищаем после теста
        db.session.rollback()

@pytest.fixture
def logged_in_client(client, new_user):
    """Клиент с авторизованным пользователем."""
    client.post('/login', data={'username': 'testuser', 'password': 'password123'})
    return client

@pytest.fixture
def developer_client(client, new_user):
    """Клиент с правами разработчика."""
    # Логин обычного пользователя
    client.post('/login', data={'username': 'testuser', 'password': 'password123'})
    
    # Логин разработчика
    client.post('/developer_login', data={'password': 'test-dev-password'})
    
    # Принудительно устанавливаем сессию разработчика для тестов
    with client.session_transaction() as sess:
        sess['developer_logged_in'] = True
    
    return client

@pytest.fixture
def second_user(app):
    """Создаем второго пользователя для тестов переводов."""
    with app.app_context():
        User.query.filter_by(username='otheruser').delete()
        db.session.commit()
        
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(username='otheruser', password=hashed_password)
        user.gossip_coins = 100
        db.session.add(user)
        db.session.commit()
        
        yield user
        
        db.session.rollback()
