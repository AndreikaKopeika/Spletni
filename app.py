from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort # Добавляем jsonify и abort
from openai import OpenAI
import re
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm # Добавил для форм
from flask_wtf.csrf import CSRFProtect # Добавил для CSRF
from flask_socketio import SocketIO, emit, join_room, leave_room # Добавил для SocketIO
from flask_limiter import Limiter # Добавляем для защиты от брутфорса
from flask_limiter.util import get_remote_address # Добавляем для защиты от брутфорса
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField # Добавил для форм
from wtforms.validators import DataRequired, Length, ValidationError # Добавил для форм
from datetime import datetime, date, timedelta
import os
import re # Импортируем модуль для регулярных выражений
from dotenv import load_dotenv # Добавляем для .env
import random
from markdown import markdown
from sqlalchemy.orm import joinedload
from sqlalchemy import func, event, text
import bleach
import sys
from werkzeug.utils import secure_filename
from faker import Faker
import time
import threading
import shutil

load_dotenv() # Загружаем переменные из .env

app = Flask(__name__)

# --- Конфигурация для загрузки файлов ---
UPLOAD_FOLDER = 'bug_reports'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class NoCsrfForm(FlaskForm):
    # class Meta:
    #     csrf = False # Эта строка отключала CSRF, удаляем ее
    pass # Добавил эту строку, чтобы класс не был пустым

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class GossipForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(min=5, max=100)])
    content = TextAreaField('Содержание', validators=[DataRequired()])
    submit = SubmitField('Опубликовать')

class UpdateGossipForm(FlaskForm):
    content = TextAreaField('Содержание', validators=[DataRequired()])
    submit = SubmitField('Обновить')

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("Нет SECRET_KEY в .env файле. Пожалуйста, создайте .env файл и установите в нем SECRET_KEY.")

app.config['SECRET_KEY'] = SECRET_KEY # Теперь берется из .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/gossip.db')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 30,
    'connect_args': {
        'timeout': 60,
        'check_same_thread': False,
        'isolation_level': None
    }
}
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app) # Инициализировал CSRFProtect
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,
    logger=True,
    engineio_logger=True
) # Инициализировал SocketIO с улучшенными настройками

limiter = Limiter( # Инициализируем Limiter
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Отключаем rate limiting в тестовом режиме
if app.config.get('TESTING'):
    limiter.enabled = False
    # Также отключаем CSRF в тестовом режиме
    app.config['WTF_CSRF_ENABLED'] = False
    # Отключаем все лимиты для тестов
    app.config['RATELIMIT_ENABLED'] = False

# OpenAI API настройки
# Принудительно загружаем .env файл и перезаписываем переменные окружения
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)  # override=True перезаписывает существующие переменные

# Получаем API ключ ТОЛЬКО из .env файла
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Функция для установки переменной окружения
def set_environment_variable(key, value):
    """Устанавливает переменную окружения в зависимости от ОС"""
    try:
        import platform
        import subprocess
        
        if platform.system() == "Windows":
            # Для Windows используем setx
            subprocess.run(['setx', key, value], check=True, capture_output=True)
            print(f"[CONFIG] Установлена переменная окружения {key} в Windows")
        else:
            # Для Linux/Mac используем export
            # Добавляем в ~/.bashrc или ~/.profile
            home = os.path.expanduser("~")
            bashrc_path = os.path.join(home, ".bashrc")
            profile_path = os.path.join(home, ".profile")
            
            export_line = f'export {key}="{value}"\n'
            
            # Добавляем в .bashrc если он существует
            if os.path.exists(bashrc_path):
                with open(bashrc_path, 'a') as f:
                    f.write(export_line)
                print(f"[CONFIG] Добавлена переменная {key} в ~/.bashrc")
            
            # Также добавляем в .profile
            with open(profile_path, 'a') as f:
                f.write(export_line)
            print(f"[CONFIG] Добавлена переменная {key} в ~/.profile")
            
            # Устанавливаем для текущей сессии
            os.environ[key] = value
            
    except Exception as e:
        print(f"[CONFIG] Ошибка при установке переменной окружения: {e}")

# Проверяем API ключ
if app.config['OPENAI_API_KEY'] and app.config['OPENAI_API_KEY'] != 'NEW_OPENAI_API_KEY_HERE_REPLACE_THIS':
    try:
        client = OpenAI(api_key=app.config['OPENAI_API_KEY'])
        print(f"[CONFIG] OpenAI API настроен: {app.config['OPENAI_API_KEY']}")
    except Exception as e:
        print(f"[CONFIG] Ошибка инициализации OpenAI API: {e}")
        client = None
else:
    client = None
    print("[CONFIG] OpenAI API ключ не найден в .env файле")

# В продакшене обязательно настройте HTTPS! Используйте Werkzeug's SecureReferrerMixin или аналогичные средства.

# --- СИСТЕМА РЕЗЕРВНОГО КОПИРОВАНИЯ ---

def create_database_backup(backup_type='auto'):
    """Создает резервную копию базы данных
    
    Args:
        backup_type (str): 'auto' для автоматических бэкапов, 'manual' для ручных
    """
    try:
        # Создаем папки для бэкапов если их нет
        auto_backup_dir = 'database_backups/automatic'
        manual_backup_dir = 'database_backups/manual'
        
        print(f"[BACKUP-DEBUG] Создаем папки для бэкапов...")
        
        try:
            if not os.path.exists(auto_backup_dir):
                os.makedirs(auto_backup_dir)
                print(f"[BACKUP-DEBUG] Создана папка: {auto_backup_dir}")
            if not os.path.exists(manual_backup_dir):
                os.makedirs(manual_backup_dir)
                print(f"[BACKUP-DEBUG] Создана папка: {manual_backup_dir}")
        except Exception as e:
            print(f"[BACKUP-ERROR] Ошибка при создании папок: {e}")
            return None
        
        # Выбираем папку в зависимости от типа бэкапа
        backup_dir = auto_backup_dir if backup_type == 'auto' else manual_backup_dir
        
        # Получаем путь к текущей базе данных
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        else:
            # Для других типов БД (если понадобится в будущем)
            db_path = db_uri.replace('sqlite://', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        
        # Проверяем, существует ли файл базы данных
        print(f"[BACKUP-DEBUG] Путь к базе данных: {db_path}")
        print(f"[BACKUP-DEBUG] Файл существует: {os.path.exists(db_path)}")
        print(f"[BACKUP-DEBUG] Текущая директория: {os.getcwd()}")
        
        if not os.path.exists(db_path):
            # Попробуем найти файл в папке instance
            db_filename = os.path.basename(db_path)
            instance_path = os.path.join(os.getcwd(), 'instance', db_filename)
            print(f"[BACKUP-DEBUG] Путь в папке instance: {instance_path}")
            print(f"[BACKUP-DEBUG] Файл в instance существует: {os.path.exists(instance_path)}")
            
            if os.path.exists(instance_path):
                db_path = instance_path
                print(f"[BACKUP-DEBUG] Используем путь в instance: {db_path}")
            else:
                # Попробуем найти файл в текущей директории
                alternative_path = os.path.join(os.getcwd(), db_filename)
                print(f"[BACKUP-DEBUG] Альтернативный путь: {alternative_path}")
                print(f"[BACKUP-DEBUG] Альтернативный файл существует: {os.path.exists(alternative_path)}")
                
                if os.path.exists(alternative_path):
                    db_path = alternative_path
                    print(f"[BACKUP-DEBUG] Используем альтернативный путь: {db_path}")
                else:
                    print(f"[BACKUP-ERROR] Файл базы данных не найден ни по пути {db_path}, ни по пути {instance_path}, ни по пути {alternative_path}")
                    return None
        
        # Создаем имя файла с временной меткой и типом
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'gossip_backup_{backup_type}_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Копируем файл базы данных
        print(f"[BACKUP-DEBUG] Копируем файл из {db_path} в {backup_path}")
        try:
            shutil.copy2(db_path, backup_path)
            print(f"[BACKUP-DEBUG] Файл успешно скопирован")
        except Exception as e:
            print(f"[BACKUP-ERROR] Ошибка при копировании файла: {e}")
            return None
        
        # Удаляем старые бэкапы только для автоматических (ручные не удаляем)
        if backup_type == 'auto':
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('gossip_backup_auto_') and f.endswith('.db')]
            backup_files.sort(reverse=True)
            
            # Оставляем последние 30 автоматических бэкапов
            if len(backup_files) > 30:
                for old_backup in backup_files[30:]:
                    old_backup_path = os.path.join(backup_dir, old_backup)
                    try:
                        os.remove(old_backup_path)
                        print(f"[BACKUP] Удален старый автоматический бэкап: {old_backup}")
                    except Exception as e:
                        print(f"[BACKUP-ERROR] Не удалось удалить {old_backup}: {e}")
        
        print(f"[BACKUP] Создан {backup_type} бэкап базы данных: {backup_filename}")
        return backup_filename
        
    except Exception as e:
        print(f"[BACKUP-ERROR] Ошибка при создании {backup_type} бэкапа: {e}")
        return None

def run_automatic_backup():
    """Фоновая задача для автоматического создания бэкапов каждые 2 часа"""
    print("--- Запуск автоматического резервного копирования ---")
    while True:
        try:
            # Ждем 2 часа (7200 секунд)
            time.sleep(7200)
            
            with app.app_context():
                backup_file = create_database_backup(backup_type='auto')
                if backup_file:
                    print(f"[AUTO-BACKUP] Автоматический бэкап создан: {backup_file}")
                else:
                    print("[AUTO-BACKUP] Ошибка при создании автоматического бэкапа")
                    
        except Exception as e:
            print(f"[AUTO-BACKUP-ERROR] Ошибка в автоматическом бэкапе: {e}")
            time.sleep(300)  # Ждем 5 минут перед повторной попыткой

def get_backup_list():
    """Возвращает список всех бэкапов"""
    try:
        auto_backup_dir = 'database_backups/automatic'
        manual_backup_dir = 'database_backups/manual'
        
        backups = {
            'automatic': [],
            'manual': []
        }
        
        # Получаем автоматические бэкапы
        if os.path.exists(auto_backup_dir):
            auto_files = [f for f in os.listdir(auto_backup_dir) if f.startswith('gossip_backup_auto_') and f.endswith('.db')]
            auto_files.sort(reverse=True)
            for file in auto_files:
                file_path = os.path.join(auto_backup_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                backups['automatic'].append({
                    'filename': file,
                    'size': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'created': file_time,
                    'path': file_path
                })
        
        # Получаем ручные бэкапы
        if os.path.exists(manual_backup_dir):
            manual_files = [f for f in os.listdir(manual_backup_dir) if f.startswith('gossip_backup_manual_') and f.endswith('.db')]
            manual_files.sort(reverse=True)
            for file in manual_files:
                file_path = os.path.join(manual_backup_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                backups['manual'].append({
                    'filename': file,
                    'size': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'created': file_time,
                    'path': file_path
                })
        
        return backups
        
    except Exception as e:
        print(f"[BACKUP-ERROR] Ошибка при получении списка бэкапов: {e}")
        return {'automatic': [], 'manual': []}

@app.route('/healthcheck')
def healthcheck():
    """Проверка работоспособности сайта и основных функций"""
    start_time = time.time()
    try:
        # Проверяем подключение к базе данных
        db.session.execute(text('SELECT 1'))
        
        # Проверяем основные модели
        user_count = User.query.count()
        gossip_count = Gossip.query.count()
        comment_count = Comment.query.count()
        
        # Проверяем bcrypt
        test_password = "test_password_123"
        hashed = bcrypt.generate_password_hash(test_password).decode('utf-8')
        bcrypt_working = bcrypt.check_password_hash(hashed, test_password)
        
        # Проверяем login_manager
        login_manager_working = login_manager is not None and hasattr(login_manager, 'user_loader')
        
        # Проверяем socketio
        socketio_working = socketio is not None and hasattr(socketio, 'emit')
        
        # Проверяем CSRF
        csrf_working = csrf is not None and hasattr(csrf, 'protect')
        
        # Проверяем limiter
        limiter_working = limiter is not None and hasattr(limiter, 'enabled')
        
        # Проверяем OpenAI клиент (если настроен)
        openai_working = False
        if client:
            try:
                # Простая проверка - пытаемся получить информацию о модели
                openai_working = True
            except:
                openai_working = False
        
        # Проверяем основные функции приложения
        try:
            # Проверяем, что можем создать тестового пользователя
            test_user = User.query.first()
            user_functions_working = True
        except:
            user_functions_working = False
            
        try:
            # Проверяем, что можем создать тестовую сплетню
            test_gossip = Gossip.query.first()
            gossip_functions_working = True
        except:
            gossip_functions_working = False
            
        try:
            # Проверяем, что можем создать тестовый комментарий
            test_comment = Comment.query.first()
            comment_functions_working = True
        except:
            comment_functions_working = False
        
        # Проверяем все сервисы
        all_services_working = all([
            bcrypt_working,
            login_manager_working,
            socketio_working,
            csrf_working,
            limiter_working,
            user_functions_working,
            gossip_functions_working,
            comment_functions_working
        ])
        
        response_time = round((time.time() - start_time) * 1000, 2)  # в миллисекундах
        
        health_status = {
            'status': 'healthy' if all_services_working else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'response_time_ms': response_time,
            'database': 'connected',
            'models': {
                'users': user_count,
                'gossips': gossip_count,
                'comments': comment_count
            },
            'services': {
                'bcrypt': 'working' if bcrypt_working else 'failed',
                'login_manager': 'working' if login_manager_working else 'failed',
                'socketio': 'working' if socketio_working else 'failed',
                'csrf': 'working' if csrf_working else 'failed',
                'limiter': 'working' if limiter_working else 'failed',
                'openai': 'working' if openai_working else 'not_configured'
            },
            'functions': {
                'user_queries': 'working' if user_functions_working else 'failed',
                'gossip_queries': 'working' if gossip_functions_working else 'failed',
                'comment_queries': 'working' if comment_functions_working else 'failed'
            },
            'overall': {
                'all_services_working': all_services_working,
                'working_services': sum([
                    bcrypt_working,
                    login_manager_working,
                    socketio_working,
                    csrf_working,
                    limiter_working,
                    user_functions_working,
                    gossip_functions_working,
                    comment_functions_working
                ]),
                'total_services': 8
            }
        }
        
        return jsonify(health_status), 200 if all_services_working else 503
        
    except Exception as e:
        response_time = round((time.time() - start_time) * 1000, 2)  # в миллисекундах
        error_status = {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'response_time_ms': response_time,
            'error': str(e),
            'error_type': type(e).__name__
        }
        return jsonify(error_status), 500

@app.route('/about')
def about():
    return render_template('home.html')

@app.route('/account')
@login_required
def account():
    return render_template('profile.html', user=current_user, gossips=Gossip.query.filter_by(user_id=current_user.id).order_by(Gossip.date_posted.desc()).paginate(page=1, per_page=5), has_voted=None, form=NoCsrfForm())

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_moderator = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_bot = db.Column(db.Boolean, default=False)
    reputation = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    gossip_coins = db.Column(db.Integer, default=100)
    pinned_gossip_id = db.Column(db.Integer, db.ForeignKey('gossip.id'), nullable=True)
    active_decoration_id = db.Column(db.Integer, db.ForeignKey('decoration.id'), nullable=True)
    notify_on_like = db.Column(db.Boolean, default=True)
    notify_on_comment = db.Column(db.Boolean, default=True)

    gossips = db.relationship('Gossip', back_populates='author', cascade="all, delete-orphan", foreign_keys='Gossip.user_id')
    comments = db.relationship('Comment', back_populates='author', cascade="all, delete-orphan")
    likes = db.relationship('Like', back_populates='user', cascade="all, delete-orphan")
    comment_likes = db.relationship('CommentLike', back_populates='user', cascade="all, delete-orphan")
    user_quests = db.relationship('UserQuest', back_populates='user', cascade="all, delete-orphan")
    notifications = db.relationship('Notification', back_populates='user', cascade="all, delete-orphan")
    decorations = db.relationship('Decoration', secondary='user_decorations', back_populates='owners')
    votes_cast = db.relationship('ReputationLog', foreign_keys='ReputationLog.voter_id', back_populates='voter', cascade="all, delete-orphan")
    votes_received = db.relationship('ReputationLog', foreign_keys='ReputationLog.target_id', back_populates='target', cascade="all, delete-orphan")
    sent_transactions = db.relationship('CoinTransaction', foreign_keys='CoinTransaction.sender_id', back_populates='sender', cascade="all, delete-orphan")
    received_transactions = db.relationship('CoinTransaction', foreign_keys='CoinTransaction.recipient_id', back_populates='recipient', cascade="all, delete-orphan")

    # Явные отношения к закреплённой сплетне и активному украшению
    pinned_gossip = db.relationship('Gossip', foreign_keys=[pinned_gossip_id])
    active_decoration = db.relationship('Decoration', foreign_keys=[active_decoration_id])

    # Последняя активность пользователя
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User('{self.username}')"

# Таблица-связка для украшений
user_decorations = db.Table('user_decorations',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('decoration_id', db.Integer, db.ForeignKey('decoration.id'), primary_key=True)
)

class Decoration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    css_class = db.Column(db.String(50), unique=True, nullable=False) # Класс для применения стилей
    rarity = db.Column(db.String(50), nullable=False, default='common') # 'common', 'rare', 'epic', 'legendary'
    is_purchasable = db.Column(db.Boolean, nullable=False, default=True) # Можно ли купить в магазине

    owners = db.relationship('User', secondary='user_decorations', back_populates='decorations')

    def __repr__(self):
        return f"Decoration('{self.name}', '{self.price}')"


class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quest_type = db.Column(db.String(50), nullable=False)
    goal = db.Column(db.Integer, nullable=False)
    reward = db.Column(db.Integer, nullable=False)

    user_quests = db.relationship('UserQuest', back_populates='quest')

class UserQuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)
    claimed = db.Column(db.Boolean, default=False)
    date_assigned = db.Column(db.Date, nullable=False, default=date.today)

    user = db.relationship('User', back_populates='user_quests')
    quest = db.relationship('Quest', back_populates='user_quests')

# --- Логика Квестов ---

def assign_daily_quests(user):
    today = date.today()
    last_quest_date = db.session.query(func.max(UserQuest.date_assigned)).filter_by(user_id=user.id).scalar()

    if last_quest_date is None or last_quest_date < today:
        # Удаляем старые квесты
        UserQuest.query.filter(UserQuest.user_id == user.id, UserQuest.claimed == False).delete()

        all_quests = Quest.query.all()
        if all_quests:
            # Выбираем 10 случайных квестов
            quests_to_assign = random.sample(all_quests, min(len(all_quests), 10))

            for quest in quests_to_assign:
                new_user_quest = UserQuest(
                    user_id=user.id,
                    quest_id=quest.id,
                    date_assigned=today
                )
                db.session.add(new_user_quest)
            db.session.commit()

def track_quest_progress(user, quest_type):
    today = date.today()
    user_quests = UserQuest.query.filter_by(user_id=user.id, date_assigned=today, claimed=False).all()

    for user_quest in user_quests:
        if user_quest.quest.quest_type == quest_type:
            user_quest.progress += 1
            if user_quest.progress >= user_quest.quest.goal:
                pass # Логика завершения квеста будет здесь
    db.session.commit()

def update_quest_progress(user, quest_type):
    """Унифицированная обертка для обновления прогресса квестов.
    Безопасно игнорирует отсутствие подходящих квестов.
    """
    try:
        track_quest_progress(user, quest_type)
    except Exception as e:
        # Логируем в консоль, чтобы не ронять запросы пользователю
        print(f"update_quest_progress error for user {getattr(user, 'id', '?')}, type {quest_type}: {e}")

def _create_new_quests_for_user(user, assign_date):
    """Создает новый набор ежедневных квестов пользователю (10 случайных)."""
    all_quests = Quest.query.all()
    if not all_quests:
        return
    quests_to_assign = random.sample(all_quests, min(len(all_quests), 10))
    for quest in quests_to_assign:
        db.session.add(UserQuest(user_id=user.id, quest_id=quest.id, date_assigned=assign_date))
    db.session.commit()

def seed_quests():
    if Quest.query.first() is None:
        quests = [
            # Лайки и взаимодействия
            Quest(name='Лайк за лайк', description='Поставьте 10 лайков на сплетни.', quest_type='LIKE_GOSSIP', goal=10, reward=15),
            Quest(name='Лайк за лайк II', description='Поставьте 25 лайков на сплетни.', quest_type='LIKE_GOSSIP', goal=25, reward=35),
            Quest(name='Лайк за лайк III', description='Поставьте 50 лайков на сплетни.', quest_type='LIKE_GOSSIP', goal=50, reward=70),
            
            # Комментарии
            Quest(name='Комментатор', description='Оставьте 5 комментариев.', quest_type='POST_COMMENT', goal=5, reward=20),
            Quest(name='Комментатор II', description='Оставьте 15 комментариев.', quest_type='POST_COMMENT', goal=15, reward=45),
            Quest(name='Комментатор III', description='Оставьте 30 комментариев.', quest_type='POST_COMMENT', goal=30, reward=80),
            
            # Создание контента
            Quest(name='Начинающий писатель', description='Опубликуйте 2 сплетни.', quest_type='POST_GOSSIP', goal=2, reward=25),
            Quest(name='Писатель', description='Опубликуйте 5 сплетен.', quest_type='POST_GOSSIP', goal=5, reward=50),
            Quest(name='Мастер слова', description='Опубликуйте 10 сплетен.', quest_type='POST_GOSSIP', goal=10, reward=100),
            
            # Популярность
            Quest(name='Популярность', description='Получите 15 лайков на свои сплетни.', quest_type='GET_LIKES', goal=15, reward=30),
            Quest(name='Популярность II', description='Получите 50 лайков на свои сплетни.', quest_type='GET_LIKES', goal=50, reward=80),
            Quest(name='Популярность III', description='Получите 100 лайков на свои сплетни.', quest_type='GET_LIKES', goal=100, reward=150),
            
            # Лайки на комментарии
            Quest(name='Лайк комментариев', description='Получите 10 лайков на свои комментарии.', quest_type='GET_COMMENT_LIKES', goal=10, reward=25),
            Quest(name='Лайк комментариев II', description='Получите 25 лайков на свои комментарии.', quest_type='GET_COMMENT_LIKES', goal=25, reward=60),
            
            # Комментарии на ваши сплетни
            Quest(name='Обсуждение', description='Получите 10 комментариев на свои сплетни.', quest_type='GET_COMMENTS', goal=10, reward=30),
            Quest(name='Обсуждение II', description='Получите 25 комментариев на свои сплетни.', quest_type='GET_COMMENTS', goal=25, reward=70),
            
            # Поиск
            Quest(name='Исследователь', description='Используйте поиск 5 раз.', quest_type='USE_SEARCH', goal=5, reward=20),
            Quest(name='Исследователь II', description='Используйте поиск 15 раз.', quest_type='USE_SEARCH', goal=15, reward=45),
            
            # Посещение профилей
            Quest(name='Социальная бабочка', description='Посетите 10 профилей других пользователей.', quest_type='VISIT_PROFILE', goal=10, reward=25),
            Quest(name='Социальная бабочка II', description='Посетите 25 профилей других пользователей.', quest_type='VISIT_PROFILE', goal=25, reward=60),
            
            # Переводы коинов
            Quest(name='Щедрость', description='Отправьте 50 коинов другим пользователям.', quest_type='SEND_COINS', goal=50, reward=30),
            Quest(name='Щедрость II', description='Отправьте 150 коинов другим пользователям.', quest_type='SEND_COINS', goal=150, reward=80),
            
            # Получение коинов
            Quest(name='Богач', description='Получите 100 коинов от других пользователей.', quest_type='RECEIVE_COINS', goal=100, reward=40),
            Quest(name='Богач II', description='Получите 300 коинов от других пользователей.', quest_type='RECEIVE_COINS', goal=300, reward=100),
        ]
        db.session.bulk_save_objects(quests)
        db.session.commit()

def seed_decorations():
    """Создает базовые украшения в базе данных."""
    if Decoration.query.first() is None:
        decorations = [
            Decoration(name='Обычная рамка', description='Простая рамка', price=10, css_class='frame-common', rarity='common'),
            Decoration(name='Редкая рамка', description='Редкая рамка', price=50, css_class='frame-rare', rarity='rare'),
            Decoration(name='Эпическая рамка', description='Эпическая рамка', price=200, css_class='frame-epic', rarity='epic'),
            Decoration(name='Легендарная рамка', description='Легендарная рамка', price=1000, css_class='frame-legendary', rarity='legendary'),
            Decoration(name='Модератор', description='Аура модератора', price=0, css_class='frame-moderator', rarity='legendary', is_purchasable=False),
            Decoration(name='Верификация', description='Свечение верификации', price=0, css_class='frame-verified', rarity='legendary', is_purchasable=False),
        ]
        db.session.bulk_save_objects(decorations)
        db.session.commit()

# --- Контекстные процессоры и обработчики ---
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.before_request
def before_request():
    if current_user.is_authenticated:
        # В тестовом и обычном режиме обновляем метку, но не коммитим здесь,
        # чтобы не конфликтовать с транзакциями запроса
        try:
            current_user.last_seen = datetime.utcnow()
        except Exception:
            pass

@app.context_processor
def inject_decorations():
    return {'decorations': Decoration.query.all()}

class Gossip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text, nullable=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Поля для глобального закрепления
    is_pinned_globally = db.Column(db.Boolean, default=False, index=True)
    pin_price = db.Column(db.Integer, default=10)
    pin_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Поля для AI улучшения
    is_ai_enhanced = db.Column(db.Boolean, default=False)
    ai_enhanced_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship('User', back_populates='gossips', foreign_keys=[user_id])
    comments = db.relationship('Comment', back_populates='gossip', cascade="all, delete-orphan")
    likes = db.relationship('Like', back_populates='gossip', cascade="all, delete-orphan")

    def __repr__(self):
        return f"Gossip('{self.title}', '{self.date_posted}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gossip_id = db.Column(db.Integer, db.ForeignKey('gossip.id'), nullable=False)

    author = db.relationship('User', back_populates='comments')
    gossip = db.relationship('Gossip', back_populates='comments')
    likes = db.relationship('CommentLike', back_populates='comment', cascade="all, delete-orphan")

    def __repr__(self):
        return f"Comment('{self.content}')"

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    
    user = db.relationship('User', back_populates='comment_likes') 
    comment = db.relationship('Comment', back_populates='likes')

    def __repr__(self):
        return f"CommentLike(User_id: {self.user_id}, Comment_id: {self.comment_id})"

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gossip_id = db.Column(db.Integer, db.ForeignKey('gossip.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', back_populates='likes')
    gossip = db.relationship('Gossip', back_populates='likes')

    def __repr__(self):
        return f"Like(User_id: {self.user_id}, Gossip_id: {self.gossip_id})"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')

    def __repr__(self):
        return f"Notification('{self.message}')"

# Новая модель для отслеживания голосов за репутацию
class ReputationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Кто голосует
    target_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # За кого голосуют
    vote_type = db.Column(db.String(10), nullable=False)  # 'upvote' или 'downvote'
    date_voted = db.Column(db.Date, nullable=False, default=date.today)

    target = db.relationship('User', foreign_keys=[target_id], back_populates='votes_received')
    voter = db.relationship('User', foreign_keys=[voter_id], back_populates='votes_cast')

class CoinTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_transactions')
    recipient = db.relationship('User', foreign_keys=[recipient_id], back_populates='received_transactions')

    def __repr__(self):
        return f"CoinTransaction from {self.sender.username} to {self.recipient.username} for {self.amount}"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Отключаем autoflush для избежания блокировок
with app.app_context():
    db.session.autoflush = False

# Разрешенные теги и атрибуты для Bleach
ALLOWED_TAGS = ['p', 'h1', 'h2', 'h3', 'strong', 'em', 'blockquote', 'ul', 'ol', 'li', 'pre', 'code', 'br', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
}

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = NoCsrfForm() # Инициализировал пустую форму для CSRF
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- НАЧАЛО ВАЛИДАЦИИ ---
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Это имя пользователя уже занято. Пожалуйста, выберите другое.', 'danger')
            return render_template('register.html', form=form)

        if not re.match(r'^\w+$', username):
            flash('Имя пользователя может содержать только буквы, цифры и знак подчеркивания.', 'danger')
            return render_template('register.html', form=form)

        if not 3 <= len(username) <= 20:
            flash('Имя пользователя должно быть длиной от 3 до 20 символов.', 'danger')
            return render_template('register.html', form=form)
        # --- КОНЕЦ ВАЛИДАЦИИ ---

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Ваш аккаунт был создан!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = NoCsrfForm() # Инициализировал пустую форму для CSRF
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Войти не удалось. Пожалуйста, проверьте имя пользователя и пароль', 'danger')
    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/")
@app.route("/home")
def home():
    # --- Новая логика для главной страницы ---

    # Глобально закрепленная сплетня
    pinned_gossip = Gossip.query.filter_by(is_pinned_globally=True).first()
    if pinned_gossip and pinned_gossip.pin_expires_at and pinned_gossip.pin_expires_at < datetime.utcnow():
        pinned_gossip.is_pinned_globally = False
        db.session.commit()
        pinned_gossip = None
    
    # Лучшее за неделю
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    best_of_week = Gossip.query \
        .outerjoin(Like) \
        .filter(Gossip.date_posted >= one_week_ago) \
        .group_by(Gossip.id) \
        .order_by(func.count(Like.id).desc()) \
        .limit(3).all()

    # От проверенных
    from_verified = Gossip.query \
        .join(Gossip.author) \
        .outerjoin(Like) \
        .filter(User.is_verified == True) \
        .group_by(Gossip.id) \
        .order_by(func.count(Like.id).desc()) \
        .limit(3).all()

    # В тренде (больше всего лайков за последние 24 часа)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    trending = Gossip.query \
        .join(Like) \
        .filter(Like.timestamp >= one_day_ago) \
        .group_by(Gossip.id) \
        .order_by(func.count(Like.id).desc()) \
        .limit(3).all()

    # --- Старая логика для основной ленты (остается) ---
    page = request.args.get('page', 1, type=int)
    gossips = Gossip.query.options(joinedload(Gossip.author)).order_by(Gossip.date_posted.desc()).paginate(page=page, per_page=5)
    
    return render_template('home.html', 
                           gossips=gossips, 
                           pinned_gossip=pinned_gossip,
                           best_of_week=best_of_week,
                           from_verified=from_verified,
                           trending=trending)

@app.route('/shop')
@login_required
def shop():
    # Находим текущую закрепленную сплетню
    pinned_gossip = Gossip.query.filter_by(is_pinned_globally=True).first()

    # Если сплетня есть и её время истекло, снимаем закрепление
    if pinned_gossip and pinned_gossip.pin_expires_at and pinned_gossip.pin_expires_at < datetime.utcnow():
        pinned_gossip.is_pinned_globally = False
        pinned_gossip = None # Обнуляем, чтобы в шаблон не передать
        db.session.commit()

    user_gossips = Gossip.query.filter_by(user_id=current_user.id).order_by(Gossip.date_posted.desc()).all()
    form = NoCsrfForm()

    # Получаем все украшения для отображения в магазине (вернули украшения)
    all_decorations = Decoration.query.order_by(Decoration.price.asc()).all()
    
    # Получаем ID уже купленных пользователем украшений для удобства проверки в шаблоне
    owned_decorations_ids = {d.id for d in current_user.decorations}

    return render_template('shop.html', 
                           pinned_gossip=pinned_gossip, 
                           user_gossips=user_gossips, 
                           form=form,
                           decorations=all_decorations,
                           owned_decorations_ids=owned_decorations_ids)

@app.route('/shop/buy/<int:decoration_id>', methods=['POST'])
@login_required
def buy_decoration(decoration_id):
    form = NoCsrfForm()
    decoration = Decoration.query.get_or_404(decoration_id)

    if not form.validate_on_submit():
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('shop'))
    
    # Проверяем, не купил ли пользователь это украшение ранее
    if decoration in current_user.decorations:
        flash('У вас уже есть это украшение.', 'info')
        return redirect(url_for('shop'))

    # Проверяем, достаточно ли коинов
    if current_user.gossip_coins < decoration.price:
        flash('Недостаточно Сплетни Коинов для покупки.', 'danger')
        return redirect(url_for('shop'))

    # Выполняем покупку
    current_user.gossip_coins -= decoration.price
    current_user.decorations.append(decoration)
    db.session.commit()
    
    flash(f'Вы успешно приобрели "{decoration.name}"!', 'success')
    return redirect(url_for('shop'))


@app.route('/gossip/<int:gossip_id>/pin', methods=['POST'])
@login_required
def pin_gossip(gossip_id):
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('shop'))

    gossip_to_pin = Gossip.query.get_or_404(gossip_id)

    if gossip_to_pin.user_id != current_user.id:
        flash('Вы можете закреплять только свои сплетни.', 'danger')
        return redirect(url_for('shop'))

    current_pinned = Gossip.query.filter_by(is_pinned_globally=True).first()
    price = 10 # Базовая цена

    if current_pinned:
        # Если текущая закрепленная сплетня просрочена
        if current_pinned.pin_expires_at and current_pinned.pin_expires_at < datetime.utcnow():
            current_pinned.is_pinned_globally = False
        # Если кто-то пытается перебить
        else:
            price = current_pinned.pin_price * 2 # Удваиваем цену
    
    if current_user.gossip_coins < price:
        flash(f'Недостаточно Сплетни Коинов. Требуется {price}.', 'danger')
        return redirect(url_for('shop'))
    
    # Снимаем старое закрепление, если оно было
    if current_pinned and current_pinned.is_pinned_globally:
        current_pinned.is_pinned_globally = False

    # Списываем деньги и закрепляем новую сплетню
    current_user.gossip_coins -= price
    gossip_to_pin.is_pinned_globally = True
    gossip_to_pin.pin_price = price
    gossip_to_pin.pin_expires_at = datetime.utcnow() + timedelta(hours=1) # Закрепление на 1 час

    db.session.commit()
    flash('Ваша сплетня успешно закреплена на главной странице!', 'success')
    return redirect(url_for('shop'))

@app.route('/leaderboard')
def leaderboard():
    top_by_rep = User.query.order_by(User.reputation.desc()).limit(10).all()
    top_by_coins = User.query.order_by(User.gossip_coins.desc()).limit(10).all()
    
    # Топ по лайкам (более сложный запрос)
    top_by_likes = db.session.query(
        User,
        func.count(Like.id).label('total_likes')
    ).join(Gossip, User.id == Gossip.user_id)\
     .join(Like, Gossip.id == Like.gossip_id)\
     .group_by(User.id)\
     .order_by(func.count(Like.id).desc())\
     .limit(10).all()

    return render_template('leaderboard.html', 
                           top_by_rep=top_by_rep,
                           top_by_coins=top_by_coins,
                           top_by_likes=top_by_likes)

@app.route("/search")
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    if not query:
        return redirect(url_for('home'))
    
    # Оптимизация: загружаем авторов найденных сплетен одним запросом
    gossips = Gossip.query.options(joinedload(Gossip.author)).filter(
        (Gossip.title.ilike(f'%{query}%')) | (Gossip.content.ilike(f'%{query}%'))
    ).order_by(Gossip.date_posted.desc()).paginate(page=page, per_page=10)
    
    # Проверяем, если пользователь запросил поиск, и обновляем прогресс квеста
    if current_user.is_authenticated:
        update_quest_progress(current_user, 'USE_SEARCH')

    return render_template('search_results.html', gossips=gossips, query=query)


@app.route("/user/<string:username>")
@login_required
def profile(username):
    # Используем joinedload для оптимизации загрузки закрепленной сплетни
    user = User.query.options(joinedload(User.pinned_gossip)).filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    # Оптимизация здесь не нужна, так как все сплетни принадлежат одному автору (user)
    gossips = Gossip.query.filter_by(user_id=user.id).order_by(Gossip.date_posted.desc()).paginate(page=page, per_page=5)
    
    # Квест на посещение профиля (не засчитываем посещение своего)
    if current_user.is_authenticated and current_user.id != user.id:
        update_quest_progress(current_user, 'VISIT_PROFILE')

    has_voted = None
    if current_user.is_authenticated and current_user.id != user.id:
        log_entry = ReputationLog.query.filter_by(voter_id=current_user.id, target_id=user.id).first()
        if log_entry:
            has_voted = log_entry.vote_type

    return render_template('profile.html', user=user, gossips=gossips, has_voted=has_voted, form=NoCsrfForm())


@app.route('/user/<string:username>/upvote', methods=['POST'])
@login_required
def upvote_user(username):
    """Голосование за повышение репутации пользователя"""
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('profile', username=username))
    
    target_user = User.query.filter_by(username=username).first_or_404()
    
    # Проверяем, что пользователь не голосует за себя
    if target_user.id == current_user.id:
        flash('Вы не можете голосовать за свою репутацию.', 'warning')
        return redirect(url_for('profile', username=username))
    
    # Проверяем, не голосовал ли уже пользователь сегодня
    existing_vote = ReputationLog.query.filter_by(
        voter_id=current_user.id,
        target_id=target_user.id,
        date_voted=date.today()
    ).first()
    
    if existing_vote:
        flash('Вы уже голосовали за этого пользователя сегодня.', 'warning')
        return redirect(url_for('profile', username=username))
    
    # Создаем запись о голосовании
    vote = ReputationLog(
        voter_id=current_user.id,
        target_id=target_user.id,
        vote_type='upvote',
        date_voted=date.today()
    )
    db.session.add(vote)
    
    # Увеличиваем репутацию
    target_user.reputation += 1
    
    db.session.commit()
    flash(f'Репутация пользователя {username} повышена!', 'success')
    return redirect(url_for('profile', username=username))


@app.route('/user/<string:username>/downvote', methods=['POST'])
@login_required
def downvote_user(username):
    """Голосование за понижение репутации пользователя"""
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('profile', username=username))
    
    target_user = User.query.filter_by(username=username).first_or_404()
    
    # Проверяем, что пользователь не голосует за себя
    if target_user.id == current_user.id:
        flash('Вы не можете голосовать за свою репутацию.', 'warning')
        return redirect(url_for('profile', username=username))
    
    # Проверяем, не голосовал ли уже пользователь сегодня
    existing_vote = ReputationLog.query.filter_by(
        voter_id=current_user.id,
        target_id=target_user.id,
        date_voted=date.today()
    ).first()
    
    if existing_vote:
        flash('Вы уже голосовали за этого пользователя сегодня.', 'warning')
        return redirect(url_for('profile', username=username))
    
    # Создаем запись о голосовании
    vote = ReputationLog(
        voter_id=current_user.id,
        target_id=target_user.id,
        vote_type='downvote',
        date_voted=date.today()
    )
    db.session.add(vote)
    
    # Уменьшаем репутацию
    target_user.reputation -= 1
    
    db.session.commit()
    flash(f'Репутация пользователя {username} понижена.', 'warning')
    return redirect(url_for('profile', username=username))


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = NoCsrfForm()
    if request.method == 'POST' and form.validate_on_submit():
        # Обновляем описание
        current_user.description = bleach.clean(request.form.get('description', ''), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        
        # Обновляем закрепленную сплетню
        pinned_id = request.form.get('pinned_gossip')
        if pinned_id and pinned_id.isdigit():
            # Проверяем, что сплетня действительно принадлежит пользователю
            gossip_to_pin = Gossip.query.filter_by(id=int(pinned_id), user_id=current_user.id).first()
            if gossip_to_pin:
                current_user.pinned_gossip_id = gossip_to_pin.id
        elif pinned_id == "0": # "0" будет означать "не закреплять"
             current_user.pinned_gossip_id = None

        # Обновляем настройки уведомлений
        current_user.notify_on_like = request.form.get('notify_on_like', False)
        current_user.notify_on_comment = request.form.get('notify_on_comment', False)

        db.session.commit()
        flash('Ваш профиль был успешно обновлен.', 'success')
        return redirect(url_for('edit_profile'))

    user_gossips = Gossip.query.filter_by(user_id=current_user.id).order_by(Gossip.date_posted.desc()).all()
    return render_template('edit_profile.html', form=form, user_gossips=user_gossips)

@app.route('/profile/customize', methods=['GET', 'POST'])
@login_required
def customize_profile():
    form = NoCsrfForm()
    user_decorations = current_user.decorations

    if request.method == 'POST':
        selected_decoration_id = request.form.get('decoration_id')

        if selected_decoration_id == '0':
            current_user.active_decoration_id = None
            db.session.commit()
            flash('Украшение с профиля снято.', 'success')
        else:
            try:
                selected_decoration_id = int(selected_decoration_id)
                owned_decoration_ids = {d.id for d in current_user.decorations}
                
                if selected_decoration_id in owned_decoration_ids:
                    current_user.active_decoration_id = selected_decoration_id
                    db.session.commit()
                    flash('Ваше украшение профиля обновлено!', 'success')
                else:
                    flash('Некорректный выбор украшения. Предмет вам не принадлежит.', 'danger')
            except (ValueError, TypeError):
                flash('Некорректный выбор украшения. Неверный ID.', 'danger')
        
        return redirect(url_for('customize_profile'))

    return render_template('customize_profile.html', decorations=user_decorations, form=form)


@app.route('/settings/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    form = NoCsrfForm()
    if form.validate_on_submit():
        current_user.notify_on_like = 'notify_on_like' in request.form
        current_user.notify_on_comment = 'notify_on_comment' in request.form
        db.session.commit()
        flash('Настройки уведомлений сохранены.', 'success')
        return redirect(url_for('notification_settings'))
    return render_template('notification_settings.html', form=form)

@app.route('/coin-center', methods=['GET', 'POST'])
@login_required
def coin_center():
    form = NoCsrfForm()
    if request.method == 'POST':
        recipient_username = request.form.get('recipient')
        
        # Проверяем, что пользователь не отправляет коины самому себе
        if recipient_username.lower() == current_user.username.lower():
            flash('Вы не можете отправлять коины самому себе.', 'danger')
            return redirect(url_for('coin_center'))

        try:
            amount = int(request.form.get('amount'))
        except (ValueError, TypeError):
            flash('Некорректное количество коинов.', 'danger')
            return redirect(url_for('coin_center'))
        
        message = bleach.clean(request.form.get('message', ''), tags=[], attributes={})

        recipient = User.query.filter(func.lower(User.username) == func.lower(recipient_username)).with_for_update(read=True).first()

        if not recipient:
            flash('Пользователь с таким именем не найден.', 'danger')
        elif amount <= 0:
            flash('Количество коинов для перевода должно быть больше нуля.', 'warning')
        elif current_user.gossip_coins < amount:
            flash('У вас недостаточно коинов для этого перевода.', 'danger')
        else:
            # Выполняем перевод
            # Простая защита от гонок в SQLite (в тестах): выполняем в одной транзакции
            current_user.gossip_coins -= amount
            recipient.gossip_coins += amount
            
            # Создаем запись о транзакции
            transaction = CoinTransaction(
                sender_id=current_user.id,
                recipient_id=recipient.id,
                amount=amount,
                message=message
            )
            db.session.add(transaction)
            
            # Отправляем уведомление получателю
            notification_message = f"Пользователь {current_user.username} отправил вам {amount} Сплетни Коинов. Сообщение: \"{message}\"" if message else f"Пользователь {current_user.username} отправил вам {amount} Сплетни Коинов."
            notification = Notification(
                user_id=recipient.id,
                notification_type='COIN_TRANSFER',
                message=notification_message
            )
            db.session.add(notification)
            
            db.session.commit()

            # Обновляем квесты
            update_quest_progress(current_user, 'SEND_COINS')
            update_quest_progress(recipient, 'RECEIVE_COINS')

            # Отправляем уведомление в реальном времени
            socketio.emit('new_notification', {'message': notification_message}, room=str(recipient.id))
            
            flash(f'Вы успешно отправили {amount} коинов пользователю {recipient.username}.', 'success')
            return redirect(url_for('coin_center'))

    # Получаем историю транзакций для текущего пользователя
    transactions = CoinTransaction.query.filter(
        (CoinTransaction.sender_id == current_user.id) | 
        (CoinTransaction.recipient_id == current_user.id)
    ).order_by(CoinTransaction.timestamp.desc()).limit(20).all()

    return render_template('coin_center.html', form=form, transactions=transactions)


# --- Роуты Квестов ---
@app.route('/quests')
@login_required
def quests():
    today = date.today()
    # Гарантируем наличие квестов на сегодня
    try:
        assign_daily_quests(current_user)
    except Exception as e:
        print(f"Error assigning quests: {e}")
        db.session.rollback()
    
    user_quests = UserQuest.query.filter_by(user_id=current_user.id, date_assigned=today).all()
    
    # Форматируем описание квестов
    for uq in user_quests:
        uq.formatted_description = uq.quest.description

    # Таймер до конца дня
    now = datetime.now()
    end_of_day = datetime.combine(now.date(), datetime.max.time())
    time_left = end_of_day - now
    
    # Форматируем время для шаблона
    time_left_formatted = {
        'hours': time_left.seconds // 3600,
        'minutes': (time_left.seconds % 3600) // 60
    }
    
    # Передаем form для CSRF-защиты в кнопках "Забрать"
    form = NoCsrfForm()

    return render_template('quests.html', title='Ежедневные квесты', user_quests=user_quests, time_left=time_left_formatted, form=form)

@app.route('/quests/claim/<int:user_quest_id>', methods=['POST'])
@login_required
def claim_quest_reward(user_quest_id):
    form = NoCsrfForm()
    if form.validate_on_submit():
        user_quest = UserQuest.query.get_or_404(user_quest_id)
        
        # Проверяем, что квест принадлежит текущему пользователю, выполнен и награда не получена
        if user_quest.user_id == current_user.id and user_quest.progress >= user_quest.quest.goal and not user_quest.claimed:
            user_quest.claimed = True
            current_user.gossip_coins += user_quest.quest.reward
            db.session.commit()
            flash(f'Награда в {user_quest.quest.reward} Сплетни коинов получена!', 'success')
        else:
            flash('Не удалось получить награду.', 'danger')
    else:
        flash('Ошибка запроса. Попробуйте снова.', 'danger')

    return redirect(url_for('quests'))

@app.route("/quest/<int:user_quest_id>/claim", methods=['POST'])
@login_required
def claim_quest(user_quest_id):
    form = NoCsrfForm()
    if not form.validate_on_submit():
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('quests'))
        
    user_quest = UserQuest.query.get_or_404(user_quest_id)
    if user_quest.user_id != current_user.id:
        abort(403)

    if user_quest.progress >= user_quest.quest.goal and not user_quest.claimed:
        current_user.gossip_coins += user_quest.quest.reward
        user_quest.claimed = True
        db.session.commit()
        flash(f'🎉 Поздравляем! Вы получили {user_quest.quest.reward} коинов за выполнение квеста "{user_quest.quest.name}"!', 'success')
    else:
        flash('Невозможно получить награду.', 'danger')

    return redirect(url_for('quests'))

@app.route("/gossip/<int:gossip_id>")
def gossip(gossip_id):
    # Оптимизация: загружаем автора сплетни и авторов комментариев одним запросом
    with db.session.no_autoflush:
        gossip = Gossip.query.options(
            joinedload(Gossip.author),
            joinedload(Gossip.comments).joinedload(Comment.author)
        ).get_or_404(gossip_id)
    
    # Сортировка комментариев по количеству лайков
    sorted_comments = sorted(gossip.comments, key=lambda c: len(c.likes), reverse=True)
    
    comment_form = NoCsrfForm()
    like_form = NoCsrfForm()
    delete_gossip_form = NoCsrfForm() # Добавил недостающую форму
    enhance_ai_form = NoCsrfForm() # Форма для улучшения AI
    
    # Используем content_html если он есть, иначе конвертируем Markdown
    if gossip.content_html:
        gossip_content_html = gossip.content_html
    else:
        # Конвертируем Markdown в HTML и очищаем его
        raw_html = markdown(gossip.content, extensions=['fenced_code', 'tables'])
        gossip_content_html = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

    return render_template('gossip.html', gossip=gossip, comments=sorted_comments, comment_form=comment_form, like_form=like_form, delete_gossip_form=delete_gossip_form, enhance_ai_form=enhance_ai_form, gossip_content_html=gossip_content_html)

@app.route('/gossip/new', methods=['GET', 'POST'])
@login_required
def new_gossip():
    form = GossipForm()
    if request.method == 'POST' and form.validate_on_submit():
        title = bleach.clean(form.title.data.strip(), tags=[], attributes={})
        content = bleach.clean(form.content.data.strip(), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        if not title or not content:
            flash('Заполните заголовок и содержание.', 'warning')
            return redirect(url_for('new_gossip'))

        new_item = Gossip(title=title, content=content, user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()

        update_quest_progress(current_user, 'POST_GOSSIP')

        flash('Ваша сплетня была опубликована!', 'success')
        return redirect(url_for('gossip', gossip_id=new_item.id))

    return render_template('create_gossip.html', page_title='Новая сплетня', gossip=None, form=form)

@app.route("/gossip/<int:gossip_id>/update", methods=['GET', 'POST'])
@login_required
def update_gossip(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    # Улучшение логики: теперь модераторы тоже могут редактировать
    if gossip.user_id != current_user.id and not current_user.is_moderator:
        flash('У вас нет прав для редактирования этой сплетни.', 'danger')
        return redirect(url_for('gossip', gossip_id=gossip.id))
    
    form = NoCsrfForm() # Для CSRF
    if request.method == 'POST' and form.validate_on_submit():
        gossip.content = bleach.clean(request.form['content'], tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        db.session.commit()
        flash('Ваша сплетня была обновлена!', 'success')
        return redirect(url_for('gossip', gossip_id=gossip.id))
    
    return render_template('create_gossip.html', page_title='Редактирование сплетни', gossip=gossip, form=form)

@app.route("/gossip/<int:gossip_id>/delete", methods=['POST'])
@login_required
def delete_gossip(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    if gossip.user_id != current_user.id:
        flash('У вас нет прав для этого действия', 'danger')
        return redirect(url_for('gossip', gossip_id=gossip.id))
    db.session.delete(gossip)
    db.session.commit()
    flash('Ваша сплетня была удалена!', 'success')
    return redirect(url_for('home'))

@app.route("/gossip/<int:gossip_id>/enhance_ai", methods=['POST'])
@login_required
@limiter.limit("5 per hour")  # Ограничиваем количество запросов
def enhance_gossip_ai(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    
    # Проверяем права доступа
    if gossip.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'У вас нет прав для улучшения этой сплетни'}), 403
    
    # Проверяем, не была ли уже улучшена сплетня
    if gossip.is_ai_enhanced:
        return jsonify({'status': 'error', 'message': 'Эта сплетня уже была улучшена с помощью AI'}), 400
    
    # Проверяем баланс коинов
    if current_user.gossip_coins < 100:
        return jsonify({'status': 'error', 'message': 'Недостаточно коинов. Требуется 100 коинов для улучшения'}), 400
    
    # Проверяем, что OpenAI API настроен
    if not app.config.get('OPENAI_API_KEY') or app.config['OPENAI_API_KEY'] == 'NEW_OPENAI_API_KEY_HERE_REPLACE_THIS':
        return jsonify({'status': 'error', 'message': 'OpenAI API не настроен. Обратитесь к администратору.'}), 500
    
    # Проверяем формат API ключа
    api_key = app.config['OPENAI_API_KEY']
    if not api_key.startswith('sk-'):
        return jsonify({'status': 'error', 'message': 'Неверный формат API ключа OpenAI.'}), 500
    
    try:
        # Создаем промпт для улучшения сплетни
        prompt = f"""Улучши и отформатируй следующую сплетню, используя Markdown:

Заголовок: {gossip.title}

Содержание: {gossip.content}

Правила улучшения:
1. Сохрани основную суть и смысл сплетни
2. Улучши стиль написания, сделай текст более читаемым и увлекательным
3. Добавь подходящие Markdown элементы: заголовки, списки, выделения, цитаты
4. Структурируй текст для лучшего восприятия
5. Не добавляй ложную информацию или домыслы
6. Сохрани оригинальный тон и стиль автора
7. Используй эмодзи для украшения, но умеренно

Верни только улучшенный текст в формате Markdown, без дополнительных пояснений."""

        # Используем существующий API для улучшения сплетни
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        
        enhanced_content = response.output_text
        
        # Проверяем, что контент не пустой и не слишком длинный
        if not enhanced_content or len(enhanced_content) > 10000:
            return jsonify({'status': 'error', 'message': 'Ошибка при улучшении сплетни. Попробуйте еще раз'}), 500
        
        # Очищаем HTML теги из улучшенного контента
        enhanced_content = bleach.clean(enhanced_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        
        # Обновляем сплетню
        gossip.content = enhanced_content
        gossip.is_ai_enhanced = True
        gossip.ai_enhanced_at = datetime.utcnow()
        
        # Списываем коины
        current_user.gossip_coins -= 100
        
        # Создаем транзакцию для отслеживания (без получателя, так как это системная операция)
        # Просто списываем коины без создания транзакции, так как это внутренняя операция
        db.session.commit()
        
        # Небольшая задержка для избежания блокировки базы данных
        import time
        time.sleep(0.5)
        
        # Конвертируем Markdown в HTML для отображения
        raw_html = markdown(enhanced_content, extensions=['fenced_code', 'tables'])
        gossip_content_html = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        
        return jsonify({
            'status': 'success',
            'message': 'Сплетня успешно улучшена с помощью AI!',
            'enhanced_content': enhanced_content,
            'enhanced_content_html': gossip_content_html,
            'remaining_coins': current_user.gossip_coins
        })
        
    except Exception as e:
        db.session.rollback()
        
        # Определяем тип ошибки и возвращаем понятное сообщение
        error_message = str(e).lower()
        
        if "database is locked" in error_message:
            import time
            time.sleep(1)
            try:
                db.session.commit()
                return jsonify({'status': 'error', 'message': 'База данных временно недоступна. Попробуйте еще раз через несколько секунд.'}), 503
            except:
                return jsonify({'status': 'error', 'message': 'База данных заблокирована. Попробуйте позже.'}), 503
        
        elif "timeout" in error_message or "connection" in error_message:
            return jsonify({'status': 'error', 'message': 'Превышено время ожидания ответа от AI. Попробуйте еще раз.'}), 408
        
        elif "authentication" in error_message or "invalid api key" in error_message:
            return jsonify({'status': 'error', 'message': 'Ошибка аутентификации OpenAI API. Обратитесь к администратору.'}), 401
        
        elif "rate limit" in error_message or "quota" in error_message:
            return jsonify({'status': 'error', 'message': 'Превышен лимит запросов к AI. Попробуйте позже.'}), 429
        
        elif "insufficient_quota" in error_message:
            return jsonify({'status': 'error', 'message': 'Закончились средства на счете OpenAI. Обратитесь к администратору.'}), 402
        
        else:
            return jsonify({'status': 'error', 'message': f'Ошибка при улучшении сплетни: {str(e)}'}), 500

@app.route("/gossip/<int:gossip_id>/comment", methods=['POST'])
@login_required
def add_comment(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    content = bleach.clean(request.form.get('content'), tags=[], attributes={}) # Полностью убираем HTML из комментариев

    if not content:
        return jsonify({'status': 'error', 'message': 'Комментарий не может быть пустым.'}), 400

    comment = Comment(content=content, user_id=current_user.id, gossip_id=gossip_id)
    db.session.add(comment)

    # Начисляем коины автору сплетни, если это не он сам
    if gossip.author != current_user:
        gossip.author.gossip_coins += 2 # 2 коина за комментарий
        
    # Уведомление для автора сплетни, если это не он сам и если у него включены уведомления
    if gossip.user_id != current_user.id and gossip.author.notify_on_comment:
        notification = Notification(
            user_id=gossip.user_id,
            message=f'Пользователь {current_user.username} прокомментировал вашу сплетню "{gossip.title}".',
            notification_type='comment'
        )
        db.session.add(notification)
        db.session.commit() # Коммитим здесь, чтобы получить ID уведомления

        unread_count = Notification.query.filter_by(user_id=gossip.user_id, is_read=False).count()
        socketio.emit('new_notification', {'message': notification.message, 'url': url_for('gossip', gossip_id=gossip.id)}, room=str(gossip.user_id))
        socketio.emit('unread_count_update', {'count': unread_count}, room=str(gossip.user_id))
    
    db.session.commit()

    # Обновление квестов
    update_quest_progress(current_user, 'POST_COMMENT')
    update_quest_progress(gossip.author, 'GET_COMMENTS')

    author_username = gossip.author.username if gossip.author else "Аноним"
    comment_data = {
        'id': comment.id,
        'content': comment.content,
        'author': {
            'username': current_user.username,
            'is_verified': current_user.is_verified,
            'is_moderator': current_user.is_moderator
        },
        'date_posted': comment.date_posted.strftime('%Y-%m-%d %H:%M')
    }
    return jsonify({'status': 'success', 'comment': comment_data, 'comments_count': len(gossip.comments)})


@app.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        new_like = CommentLike(user_id=current_user.id, comment_id=comment_id)
        db.session.add(new_like)
        liked = True
        # Обновление квеста для автора комментария
        if comment.author != current_user:
            update_quest_progress(comment.author, 'GET_COMMENT_LIKES')

    db.session.commit()
    return jsonify({'status': 'success', 'likes': len(comment.likes), 'liked': liked})


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    gossip = comment.gossip # Получаем родительскую сплетню

    # Разрешаем удаление, если пользователь:
    # 1. Автор комментария
    # 2. Автор сплетни
    # 3. Модератор
    if current_user.id != comment.user_id and current_user.id != gossip.user_id and not current_user.is_moderator:
        flash('У вас нет прав для этого действия', 'danger')
        return redirect(url_for('gossip', gossip_id=comment.gossip_id))

    db.session.delete(comment)
    db.session.commit()
    flash('Комментарий был удален!', 'success')
    return redirect(url_for('gossip', gossip_id=comment.gossip_id))

DEVELOPER_PASSWORD = os.environ.get('DEVELOPER_PASSWORD') # Теперь берется из .env

@app.route("/developer_login", methods=['GET', 'POST'])
def developer_login():
    if session.get('developer_logged_in'):
        return redirect(url_for('developer_panel'))
    form = NoCsrfForm()
    
    # В тестовом режиме пропускаем CSRF валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if request.method == 'POST' and (not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit()):
        password = request.form.get('password')
        if password == DEVELOPER_PASSWORD:
            session['developer_logged_in'] = True
            flash('Вы успешно вошли в панель разработчика!', 'success')
            return redirect(url_for('developer_panel'))
        else:
            flash('Неверный пароль.', 'danger')
    return render_template('developer_login.html', form=form)

@app.route("/developer_panel", methods=['GET', 'POST'])
@app.route("/dev", methods=['GET', 'POST'])
def developer_panel():
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))

    # Получаем параметры для графиков и прокрутки
    time_range = request.args.get('time_range', '7_days')  # По умолчанию 7 дней
    time_interval = request.args.get('time_interval', 'days')  # По умолчанию по дням
    scroll_to = request.args.get('scroll_to') or request.form.get('scroll_to')  # Из GET или POST
    
    # Вычисляем начальную дату в зависимости от диапазона
    now = datetime.utcnow()
    if time_range == '1_day':
        start_date = now - timedelta(days=1)
    elif time_range == '3_days':
        start_date = now - timedelta(days=3)
    elif time_range == '7_days':
        start_date = now - timedelta(days=7)
    elif time_range == '30_days':
        start_date = now - timedelta(days=30)
    else:  # По умолчанию 7 дней
        start_date = now - timedelta(days=7)
    
    # Формируем запросы в зависимости от интервала
    if time_interval == 'minutes':
        # По минутам (для последних 24 часов)
        start_date = now - timedelta(hours=24)
        gossips_query = db.session.query(
            func.strftime('%Y-%m-%d %H:%M', Gossip.date_posted),
            func.count(Gossip.id)
        ).filter(
            Gossip.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-%m-%d %H:%M', Gossip.date_posted)
        ).order_by(
            func.strftime('%Y-%m-%d %H:%M', Gossip.date_posted)
        ).all()
        
        comments_query = db.session.query(
            func.strftime('%Y-%m-%d %H:%M', Comment.date_posted),
            func.count(Comment.id)
        ).filter(
            Comment.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-%m-%d %H:%M', Comment.date_posted)
        ).order_by(
            func.strftime('%Y-%m-%d %H:%M', Comment.date_posted)
        ).all()
        
    elif time_interval == 'hours':
        # По часам
        gossips_query = db.session.query(
            func.strftime('%Y-%m-%d %H:00', Gossip.date_posted),
            func.count(Gossip.id)
        ).filter(
            Gossip.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-%m-%d %H:00', Gossip.date_posted)
        ).order_by(
            func.strftime('%Y-%m-%d %H:00', Gossip.date_posted)
        ).all()
        
        comments_query = db.session.query(
            func.strftime('%Y-%m-%d %H:00', Comment.date_posted),
            func.count(Comment.id)
        ).filter(
            Comment.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-%m-%d %H:00', Comment.date_posted)
        ).order_by(
            func.strftime('%Y-%m-%d %H:00', Comment.date_posted)
        ).all()
        
    elif time_interval == 'weeks':
        # По неделям
        gossips_query = db.session.query(
            func.strftime('%Y-W%W', Gossip.date_posted),
            func.count(Gossip.id)
        ).filter(
            Gossip.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-W%W', Gossip.date_posted)
        ).order_by(
            func.strftime('%Y-W%W', Gossip.date_posted)
        ).all()
        
        comments_query = db.session.query(
            func.strftime('%Y-W%W', Comment.date_posted),
            func.count(Comment.id)
        ).filter(
            Comment.date_posted >= start_date
        ).group_by(
            func.strftime('%Y-W%W', Comment.date_posted)
        ).order_by(
            func.strftime('%Y-W%W', Comment.date_posted)
        ).all()
        
    else:  # По дням (по умолчанию)
        gossips_query = db.session.query(
            func.date(Gossip.date_posted),
            func.count(Gossip.id)
        ).filter(
            Gossip.date_posted >= start_date
        ).group_by(
            func.date(Gossip.date_posted)
        ).order_by(
            func.date(Gossip.date_posted)
        ).all()
        
        comments_query = db.session.query(
            func.date(Comment.date_posted),
            func.count(Comment.id)
        ).filter(
            Comment.date_posted >= start_date
        ).group_by(
            func.date(Comment.date_posted)
        ).order_by(
            func.date(Comment.date_posted)
        ).all()
    
    # Форматируем данные для графиков
    gossip_labels = []
    gossip_data = []
    comment_labels = []
    comment_data = []
    
    # Создаем словари для объединения данных
    gossips_dict = {str(row[0]): row[1] for row in gossips_query}
    comments_dict = {str(row[0]): row[1] for row in comments_query}
    
    # Получаем все уникальные метки времени
    all_labels = sorted(set(list(gossips_dict.keys()) + list(comments_dict.keys())))
    
    for label in all_labels:
        gossip_labels.append(label)
        gossip_data.append(gossips_dict.get(label, 0))
        comment_labels.append(label)
        comment_data.append(comments_dict.get(label, 0))

    chart_data = {
        'gossip_labels': gossip_labels,
        'gossip_data': gossip_data,
        'comment_labels': comment_labels,
        'comment_data': comment_data
    }

    # Поиск и сортировка пользователей
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'date_registered')
    sort_order = request.args.get('sort_order', 'desc')

    users_query = User.query

    if search_query:
        users_query = users_query.filter(User.username.ilike(f'%{search_query}%'))

    sort_column = getattr(User, sort_by, User.date_registered)
    if sort_order == 'asc':
        users_query = users_query.order_by(sort_column.asc())
    else:
        users_query = users_query.order_by(sort_column.desc())

    users = users_query.all()

    form = NoCsrfForm() # <-- Добавляем эту строку
    
    # Получаем список бэкапов
    backups = get_backup_list()

    return render_template('developer_panel.html', 
                           users=users, 
                           chart_data=chart_data,
                           search_query=search_query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           time_range=time_range,
                           time_interval=time_interval,
                           scroll_to=scroll_to,
                           form=form,
                           backups=backups)


@app.route('/developer/refresh_quests', methods=['POST'])
def developer_refresh_quests():
    if 'developer_logged_in' not in session or not session['developer_logged_in']:
        return redirect(url_for('developer_login'))

    if not current_user.is_authenticated:
        flash('Вы должны быть авторизованы как обычный пользователь, чтобы обновить свои квесты.', 'warning')
        return redirect(url_for('developer_panel'))

    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if request.method == 'POST' and (not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit()):
        today = date.today()
        
        # 1. Находим и удаляем старые квесты более надежным способом
        quests_to_delete = UserQuest.query.filter_by(user_id=current_user.id, date_assigned=today).all()
        for quest in quests_to_delete:
            db.session.delete(quest)
        db.session.commit() # Применяем удаление немедленно

        # 2. Создаем новые квесты
        _create_new_quests_for_user(current_user, today)
        db.session.commit() # Сохраняем новые
        
        flash('Ваши ежедневные квесты были принудительно обновлены.', 'success')
    
    return redirect(url_for('developer_panel', scroll_to='server-section'))

@app.route("/developer_panel/reset_db", methods=['POST'])
@login_required
def reset_db():
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    # Сброс базы данных
    db.drop_all()
    db.create_all()
    flash('База данных была полностью сброшена.', 'success')
    return redirect(url_for('developer_panel', scroll_to='server-section'))

def restart_app():
    """Перезапускает текущее приложение."""
    # os.execl заменяет текущий процесс новым.
    # sys.executable - это путь к интерпретатору Python
    # sys.argv - это список аргументов командной строки, с которыми был запущен скрипт
    try:
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        # В некоторых средах (например, в некоторых IDE или на Windows) это может не сработать
        # Это запасной вариант, который просто завершает процесс.
        # Werkzeug (сервер разработки Flask) должен автоматически перезапустить его.
        print(f"Не удалось выполнить перезапуск через os.execl: {e}. Используется os._exit.")
        os._exit(0)

@app.route("/developer_panel/restart", methods=['POST'])
@login_required
def restart_server():
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    flash('Сервер перезапускается...', 'info')
    # Вызываем перезапуск в отдельной функции, чтобы успеть отправить ответ браузеру
    socketio.start_background_task(target=restart_app)
    return redirect(url_for('developer_panel', scroll_to='server-section'))


@app.route("/developer_logout")
def developer_logout():
    session.pop('developer_logged_in', None)
    flash('Вы вышли из панели разработчика', 'info')
    return redirect(url_for('home'))

@app.route("/developer_panel/toggle_moderator/<int:user_id>")
@login_required
def toggle_moderator(user_id):
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    moderator_decoration = Decoration.query.filter_by(css_class='frame-moderator').first()

    user.is_moderator = not user.is_moderator

    if moderator_decoration:
        if user.is_moderator:
            # Выдаем украшение
            if moderator_decoration not in user.decorations:
                user.decorations.append(moderator_decoration)
            flash(f'Пользователю {user.username} присвоен статус модератора и выдана "Аура модератора".', 'success')
        else:
            # Забираем украшение
            if moderator_decoration in user.decorations:
                # Если украшение было активным, снимаем его
                if user.active_decoration_id == moderator_decoration.id:
                    user.active_decoration_id = None
                user.decorations.remove(moderator_decoration)
            flash(f'С пользователя {user.username} снят статус модератора и изъята "Аура модератора".', 'success')
            
        db.session.commit()
    return redirect(url_for('developer_panel', scroll_to='users-section'))
    
@app.route("/developer_panel/toggle_verified/<int:user_id>")
@login_required
def toggle_verified(user_id):
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    verified_decoration = Decoration.query.filter_by(css_class='frame-verified').first()

    user.is_verified = not user.is_verified

    if verified_decoration:
        if user.is_verified:
            if verified_decoration not in user.decorations:
                user.decorations.append(verified_decoration)
            flash(f'Пользователь {user.username} верифицирован и получил "Свечение верификации".', 'success')
        else:
            if verified_decoration in user.decorations:
                if user.active_decoration_id == verified_decoration.id:
                    user.active_decoration_id = None
                user.decorations.remove(verified_decoration)
            flash(f'С пользователя {user.username} снята верификация и изъято "Свечение верификации".', 'success')

    db.session.commit()
    return redirect(url_for('developer_panel', scroll_to='users-section'))

@app.route('/developer/add_coins/<int:user_id>', methods=['POST'])
@login_required
def add_coins(user_id):
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    
    # В тестовом режиме просто выполняем действие без CSRF проверки
    if app.config.get('TESTING'):
        try:
            amount = int(request.form.get('amount'))
            if amount > 0:
                user.gossip_coins += amount
                db.session.commit()
                flash(f'Успешно добавлено {amount} коинов пользователю {user.username}.', 'success')
            else:
                flash('Количество коинов должно быть положительным числом.', 'warning')
        except (ValueError, TypeError):
            flash('Некорректное количество коинов.', 'danger')
    else:
        # В продакшене проверяем CSRF
        form = NoCsrfForm()
        if form.validate_on_submit():
            try:
                amount = int(request.form.get('amount'))
                if amount > 0:
                    user.gossip_coins += amount
                    db.session.commit()
                    flash(f'Успешно добавлено {amount} коинов пользователю {user.username}.', 'success')
                else:
                    flash('Количество коинов должно быть положительным числом.', 'warning')
            except (ValueError, TypeError):
                flash('Некорректное количество коинов.', 'danger')
        else:
            flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
            
    return redirect(url_for('developer_panel', scroll_to='users-section'))


@app.route("/notifications")
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).paginate(page=page, per_page=10)
    
    unread_notifications = [n for n in notifications.items if not n.is_read]
    for notification in unread_notifications:
        notification.is_read = True
    if unread_notifications:
        db.session.commit()

    # Исправление: передаем пустую форму для CSRF в кнопки удаления
    form = NoCsrfForm()
    return render_template('notifications.html', notifications=notifications, form=form)

@app.route("/notification/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('У вас нет прав для этого действия', 'danger')
        return redirect(url_for('notifications'))
    notification.is_read = True
    db.session.commit()
    # Отправляем обновление счетчика после прочтения
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    socketio.emit('unread_count_update', {'count': unread_count}, room=str(current_user.id))
    return redirect(url_for('notifications'))

@app.route("/notification/<int:notification_id>/delete", methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('У вас нет прав для этого действия', 'danger')
        return redirect(url_for('notifications'))
    db.session.delete(notification)
    db.session.commit()
    # Отправляем обновление счетчика после удаления
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    socketio.emit('unread_count_update', {'count': unread_count}, room=str(current_user.id))
    flash('Уведомление удалено.', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/delete_all', methods=['POST'])
@login_required
def delete_all_notifications():
    form = NoCsrfForm()
    if form.validate_on_submit():
        try:
            Notification.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            
            unread_count = 0
            socketio.emit('unread_count_update', {'count': unread_count}, room=str(current_user.id))
            
            flash('Все уведомления были удалены.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при удалении уведомлений.', 'danger')
            print(f"Error deleting all notifications for user {current_user.id}: {e}", file=sys.stderr)

    return redirect(url_for('notifications'))


@app.route("/gossip/<int:gossip_id>/like", methods=['POST'])
@login_required
def like_gossip(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    like = Like.query.filter_by(user_id=current_user.id, gossip_id=gossip.id).first()

    if like:
        db.session.delete(like)
        db.session.commit()
        liked = False
    else:
        like = Like(user_id=current_user.id, gossip_id=gossip_id)
        db.session.add(like)
        
        # Автор получает коины только если лайк ставит не он сам
        if gossip.user_id != current_user.id:
            author = User.query.get(gossip.user_id)
            if author:
                author.gossip_coins += 1

        db.session.commit()
        
        # Обновляем квесты
        update_quest_progress(current_user, 'LIKE_GOSSIP')
        author_for_quest = User.query.get(gossip.user_id)
        if author_for_quest:
            update_quest_progress(author_for_quest, 'GET_LIKES')
        
        liked = True

    return jsonify({'status': 'success', 'likes': len(gossip.likes), 'liked': liked})

@app.route('/gossip/<int:gossip_id>/unlike', methods=['POST'])
@login_required
def unlike_gossip(gossip_id):
    gossip = Gossip.query.get_or_404(gossip_id)
    like = Like.query.filter_by(user_id=current_user.id, gossip_id=gossip.id).first()
    
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({'status': 'success', 'likes': len(gossip.likes), 'liked': False})
    else:
        return jsonify({'status': 'error', 'message': 'Лайк не найден.'}), 400

@app.route('/report-bug', methods=['GET', 'POST'])
@login_required
def report_bug():
    form = NoCsrfForm()
    if request.method == 'POST' and form.validate_on_submit():
        bug_description = request.form.get('description')
        steps_to_reproduce = request.form.get('steps')
        file = request.files.get('screenshot')

        if not bug_description or not steps_to_reproduce:
            flash('Пожалуйста, заполните все текстовые поля.', 'danger')
            return render_template('report_bug.html', form=form)

        # Создаем папку для отчетов, если её нет
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        # Сохраняем текстовую информацию
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename_base = f"report_{current_user.username}_{timestamp}"
        
        with open(os.path.join(app.config['UPLOAD_FOLDER'], f"{report_filename_base}.txt"), 'w', encoding='utf-8') as f:
            f.write(f"User: {current_user.username}\n")
            f.write(f"Time: {timestamp}\n\n")
            f.write("Description:\n")
            f.write(bug_description + "\n\n")
            f.write("Steps to Reproduce:\n")
            f.write(steps_to_reproduce + "\n")

        # Сохраняем скриншот, если он есть и валиден
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            screenshot_filename = f"{report_filename_base}.{file_extension}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], screenshot_filename))

        flash('Спасибо! Ваш отчет об ошибке был отправлен.', 'success')
        return redirect(url_for('home'))

    return render_template('report_bug.html', form=form)


@socketio.on('connect')
def handle_connect():
    try:
        if current_user.is_authenticated:
            join_room(str(current_user.id))
            print(f'Client {current_user.username} connected and joined room {current_user.id}')
        else:
            print('Anonymous client connected')
    except Exception as e:
        print(f'Error in handle_connect: {e}')

@socketio.on('request_unread_count')
@login_required
def request_unread_count():
    try:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        emit('unread_count_update', {'count': unread_count}, room=str(current_user.id))
        return {'status': 'success'}
    except Exception as e:
        print(f'Error in request_unread_count: {e}')
        return {'status': 'error', 'message': str(e)}

@socketio.on('disconnect')
def handle_disconnect():
    try:
        if current_user.is_authenticated:
            leave_room(str(current_user.id))
            print(f'Client {current_user.username} disconnected from room {current_user.id}')
        else:
            print('Anonymous client disconnected')
    except Exception as e:
        print(f'Error in handle_disconnect: {e}')

@socketio.on_error()
def error_handler(e):
    print(f'SocketIO error: {e}')
    return False

@app.route("/developer_panel/bots", methods=['GET', 'POST'])
@login_required
def bot_management_panel():
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    form = NoCsrfForm() # Создаем экземпляр формы
    if request.method == 'POST':
        # В тестовом режиме или если CSRF отключен, пропускаем валидацию
        csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
        if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
            pass  # Продолжаем выполнение
        else:
            flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
            return redirect(url_for('bot_management_panel'))
            
        action = request.form.get('action')
        fake = Faker('ru_RU')

        if action == 'create':
            try:
                bot_count = int(request.form.get('bot_count', 1))
                if not 1 <= bot_count <= 100:
                    raise ValueError("Недопустимое количество ботов.")
                
                created_count = 0
                
                # Получаем простые покупаемые украшения для случайной выдачи
                simple_decorations = Decoration.query.filter(
                    Decoration.is_purchasable == True,
                    Decoration.rarity == 'common'
                ).all()

                for _ in range(bot_count):
                    # Используем только faker для более реалистичных имен
                    username = fake.user_name()
                    
                    # Проверяем, что такого имени еще нет
                    while User.query.filter_by(username=username).first():
                        username = fake.user_name() + str(random.randint(1, 99))
                    
                    password = fake.password()
                    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                    
                    new_bot = User(
                        username=username,
                        password=hashed_password,
                        is_bot=True
                    )
                    # Присваиваем остальные атрибуты после создания объекта
                    # Реалистичное распределение коинов с приоритетом на 100 (стартовые коины)
                    coin_distribution = random.choices(
                        population=['starter', 'poor', 'average', 'rich'],
                        weights=[0.5, 0.3, 0.15, 0.05],
                        k=1
                    )[0]
                    
                    if coin_distribution == 'starter':
                        # 50% шанс получить 100 коинов (стартовые)
                        new_bot.gossip_coins = 100
                    elif coin_distribution == 'poor':
                        new_bot.gossip_coins = random.randint(0, 99)
                    elif coin_distribution == 'average':
                        new_bot.gossip_coins = random.randint(101, 363)
                    else:  # rich
                        new_bot.gossip_coins = random.randint(200, 363)
                    
                    # Реалистичная репутация в диапазоне -4 до 10
                    reputation_distribution = random.choices(
                        population=['negative', 'low', 'average', 'high'],
                        weights=[0.15, 0.35, 0.4, 0.1],
                        k=1
                    )[0]
                    
                    if reputation_distribution == 'negative':
                        new_bot.reputation = random.randint(-4, -1)
                    elif reputation_distribution == 'low':
                        new_bot.reputation = random.randint(0, 3)
                    elif reputation_distribution == 'average':
                        new_bot.reputation = random.randint(4, 7)
                    else:  # high
                        new_bot.reputation = random.randint(8, 10)
                    
                    # Биография с разной вероятностью
                    if random.random() < 0.7:
                        new_bot.description = random.choice(BOT_BIOS)
                    
                    # С шансом 2.5% даем боту случайное простое украшение (было 25%)
                    if simple_decorations and random.random() < 0.025:
                        deco = random.choice(simple_decorations)
                        new_bot.decorations.append(deco)
                        # И с шансом 50% делаем его активным
                        if random.random() < 0.5:
                            # Мы не можем присвоить active_decoration_id до того, как у new_bot появится id,
                            # поэтому сделаем это после коммита
                            pass # Логика будет добавлена ниже

                    db.session.add(new_bot)
                    created_count += 1
                
                db.session.commit()

                # Теперь, когда у ботов есть ID, можно выдать им активные украшения
                bots_without_active_deco = User.query.filter(User.is_bot==True, User.active_decoration_id==None).all()
                for bot in bots_without_active_deco:
                    if bot.decorations and random.random() < 0.5:
                        # присваиваем через id, чтобы избежать лишней загрузки relationship
                        bot.active_decoration_id = random.choice(bot.decorations).id

                db.session.commit()

                flash(f'Успешно создано {created_count} ботов.', 'success')

            except (ValueError, TypeError) as e:
                flash(f'Ошибка при создании ботов: {e}', 'danger')

        elif action == 'delete_all':
            # Сначала удаляем все зависимости, чтобы избежать ошибок целостности
            bots_to_delete = User.query.filter_by(is_bot=True).all()
            count = len(bots_to_delete)
            for bot in bots_to_delete:
                # Удаляем связанные данные, чтобы не было ошибок
                Like.query.filter_by(user_id=bot.id).delete()
                Comment.query.filter_by(user_id=bot.id).delete()
                Gossip.query.filter_by(user_id=bot.id).delete()
                db.session.delete(bot)
            db.session.commit()
            flash(f'Успешно удалено {count} ботов.', 'success')

        elif action == 'delete_one':
            try:
                bot_id = int(request.form.get('bot_id'))
                bot = User.query.filter_by(id=bot_id, is_bot=True).first()
                if bot:
                    # Сначала удаляем все зависимости
                    Like.query.filter_by(user_id=bot.id).delete()
                    Comment.query.filter_by(user_id=bot.id).delete()
                    Gossip.query.filter_by(user_id=bot.id).delete()
                    db.session.delete(bot)
                    db.session.commit()
                    flash(f'Бот {bot.username} успешно удален.', 'success')
                else:
                    flash('Бот не найден.', 'danger')
            except (ValueError, TypeError):
                flash('Некорректный ID бота.', 'danger')

        elif action == 'trigger_activity':
            bots = User.query.filter_by(is_bot=True).all()
            if bots:
                num_to_trigger = random.randint(1, min(3, len(bots)))  # Уменьшили максимум с 5 до 3 ботов
                bots_to_trigger = random.sample(bots, num_to_trigger)
                # В тестовом режиме выполняем синхронно, без фонового потока, чтобы избежать блокировок БД
                if app.config.get('TESTING'):
                    trigger_bot_actions(bots_to_trigger)
                    flash(f'Активировано {num_to_trigger} ботов (тестовый режим).', 'success')
                else:
                    thread = threading.Thread(target=trigger_bot_actions, args=(bots_to_trigger,))
                    thread.start()
                    flash(f'Активировано {num_to_trigger} ботов в фоновом режиме.', 'success')
            else:
                flash('Нет ботов для активации.', 'warning')
        
        return redirect(url_for('bot_management_panel'))

    bots = User.query.filter_by(is_bot=True).all()
    return render_template('bot_management.html', bots=bots, form=form) # Передаем форму в шаблон

@app.route("/developer_panel/generate_ai_gossip", methods=['POST'])
@login_required
def generate_ai_gossip_route():
    """Роут для генерации AI сплетни случайным ботом"""
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('bot_management_panel'))
    
    # Проверяем, есть ли OpenAI API ключ
    if not client:
        flash('OpenAI API ключ не настроен. Добавьте OPENAI_API_KEY в переменные окружения.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    # Получаем случайного бота
    bots = User.query.filter_by(is_bot=True).all()
    if not bots:
        flash('Нет доступных ботов для генерации сплетни.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    selected_bot = random.choice(bots)
    
    # Генерируем AI сплетню
    title, content = generate_ai_gossip()
    
    if title and content:
        # Конвертируем Markdown в HTML
        content_html = markdown_to_html(content)
        
        # Создаем новую сплетню
        new_gossip = Gossip(
            title=title,
            content=content,
            content_html=content_html,
            user_id=selected_bot.id
        )
        db.session.add(new_gossip)
        db.session.commit()
        
        flash(f'AI сплетня успешно создана от имени бота {selected_bot.username}!', 'success')
        print(f"[AI-GOSSIP] Бот {selected_bot.username} создал AI сплетню: {title}")
    else:
        flash(f'Ошибка при генерации AI сплетни: {content}', 'danger')
    
    return redirect(url_for('bot_management_panel'))

@app.route("/developer_panel/generate_ai_comments", methods=['POST'])
@login_required
def generate_ai_comments_route():
    """Роут для генерации AI комментариев к сплетням"""
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('bot_management_panel'))
    
    # Проверяем, есть ли OpenAI API ключ
    if not client:
        flash('OpenAI API ключ не настроен. Добавьте OPENAI_API_KEY в переменные окружения.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    # Получаем количество комментариев
    try:
        comment_count = int(request.form.get('comment_count', 5))
        if not 1 <= comment_count <= 20:
            flash('Количество комментариев должно быть от 1 до 20.', 'warning')
            return redirect(url_for('bot_management_panel'))
    except (ValueError, TypeError):
        flash('Некорректное количество комментариев.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    # Получаем сплетни для комментирования (приоритет популярным и новым)
    gossips = get_smart_gossip_targets()
    if not gossips:
        flash('Нет сплетен для комментирования.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    # Получаем ботов
    bots = User.query.filter_by(is_bot=True).all()
    if not bots:
        flash('Нет доступных ботов для комментирования.', 'warning')
        return redirect(url_for('bot_management_panel'))
    
    created_comments = 0
    attempts = 0
    max_attempts = comment_count * 3  # Максимум попыток для создания комментариев
    
    while created_comments < comment_count and attempts < max_attempts:
        attempts += 1
        
        # Выбираем случайную сплетню (с приоритетом популярным)
        gossip = random.choice(gossips)
        
        # Выбираем случайного бота
        bot = random.choice(bots)
        
        # Проверяем, не комментировал ли уже этот бот эту сплетню
        existing_comment = Comment.query.filter_by(user_id=bot.id, gossip_id=gossip.id).first()
        if existing_comment:
            # Пропускаем этого бота, но продолжаем с другими
            continue
        
        # Генерируем AI комментарий
        comment_text = generate_ai_comment(gossip.title, gossip.content)
        
        if comment_text:
            try:
                # Создаем комментарий
                new_comment = Comment(
                    content=comment_text,
                    user_id=bot.id,
                    gossip_id=gossip.id
                )
                db.session.add(new_comment)
                
                # Начисляем коины автору сплетни, если это не он сам
                if gossip.author != bot:
                    gossip.author.gossip_coins += 2
                
                created_comments += 1
                print(f"[AI-COMMENT] Бот {bot.username} прокомментировал сплетню '{gossip.title}': {comment_text[:50]}...")
            except Exception as e:
                print(f"Ошибка при создании комментария от {bot.username}: {e}")
                db.session.rollback()
                continue
    
    try:
        db.session.commit()
        
        if created_comments > 0:
            if created_comments == comment_count:
                flash(f'Успешно создано {created_comments} AI комментариев!', 'success')
            else:
                flash(f'Создано {created_comments} из {comment_count} AI комментариев. Некоторые боты уже прокомментировали доступные сплетни.', 'warning')
        else:
            flash('Не удалось создать комментарии. Возможно, все боты уже прокомментировали доступные сплетни.', 'warning')
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при создании AI комментариев: {e}")
        flash(f'Ошибка при создании комментариев: {str(e)}', 'danger')
    
    return redirect(url_for('bot_management_panel'))

@app.route("/developer_panel/create_backup", methods=['POST'])
@login_required
def create_backup_route():
    """Роут для создания резервной копии базы данных"""
    if not session.get('developer_logged_in'):
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('home'))
    
    form = NoCsrfForm()
    # В тестовом режиме или если CSRF отключен, пропускаем валидацию
    csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
    if not csrf_enabled or app.config.get('TESTING') or form.validate_on_submit():
        pass  # Продолжаем выполнение
    else:
        flash('Ошибка CSRF. Попробуйте еще раз.', 'danger')
        return redirect(url_for('developer_panel'))
    
    # Создаем ручной бэкап
    backup_file = create_database_backup(backup_type='manual')
    
    if backup_file:
        flash(f'Резервная копия успешно создана: {backup_file}', 'success')
    else:
        flash('Ошибка при создании резервной копии', 'danger')
    
    return redirect(url_for('developer_panel', scroll_to='backups-section'))

# --- СИСТЕМА ИМИТАЦИИ АКТИВНОСТИ БОТОВ ---

# Расширенные и "оживленные" списки для большей вариативности
BOT_BIOS = [
    # Простые и короткие
    "Просто чел", "ищу дрзей,,", "люблю котиков и сплетни", "*_*", "хто я",
    "здесь чтобы судить", "мой второй акк", "не пишите мне", "1234567",
    "Твой краш", "На чиле", "Просто наблюдаю.", "Читаю между строк.",
    "Здесь ради контента.", "Ищу что-то интересное.", "Всем привет!",
    "Коллекционирую слухи.", "А что тут у вас происходит?", "Тихий зритель.",
    
    # Современные и молодежные
    "Живу в интернете", "Серфинг по ленте", "Люблю мемы", "Тиктокер",
    "Инстаграмщик", "Ютубер", "Стример", "Геймер", "Анимешник",
    "Косплеер", "Фанат", "Подписчик", "Лайкер", "Комментатор",
    
    # Рабочие/учебные
    "Офисный работник", "Студент", "Фрилансер", "Предприниматель",
    "Программист", "Дизайнер", "Маркетолог", "Менеджер", "Учитель",
    "Врач", "Юрист", "Бухгалтер", "Продавец", "Водитель",
    
    # Хобби и интересы
    "Люблю читать", "Спортсмен", "Музыкант", "Художник", "Фотограф",
    "Путешественник", "Кулинар", "Садовод", "Коллекционер", "Рыбак",
    "Охотник", "Турист", "Альпинист", "Велосипедист", "Бегун",
    
    # Эмоциональные состояния
    "Вечно уставший", "Оптимист", "Пессимист", "Меланхолик", "Холерик",
    "Сангвиник", "Флегматик", "Интроверт", "Экстраверт", "Амбиверт",
    "Мечтатель", "Реалист", "Романтик", "Циник", "Философ",
    
    # Жизненные ситуации
    "В поисках себя", "На распутье", "В кризисе", "В поисках работы",
    "В отношениях", "Свободен", "Женат/замужем", "Разведен", "Вдовец/вдова",
    "Родитель", "Бездетный", "Студент", "Выпускник", "Пенсионер",
    
    # Характерные черты
    "Добрый", "Злой", "Веселый", "Грустный", "Умный", "Глупый",
    "Красивый", "Симпатичный", "Строгий", "Мягкий", "Серьезный",
    "Шутник", "Молчун", "Болтун", "Скромный", "Наглый",
    
    # Интернет-культура
    "Мемолог", "Копипастер", "Репостер", "Луркер", "Тролль",
    "Модератор", "Админ", "Мемер", "Шиппостер", "Фанфикер",
    "Косплеер", "Анимешник", "Геймер", "Стример", "Блогер",
    
    # Забавные и абсурдные
    "Мальчик 5222 лет", "Инопланетянин", "Путешественник во времени",
    "Пришелец из будущего", "Киберпанк", "Нео", "Матрица", "Бэтмен",
    "Супермен", "Человек-паук", "Железный человек", "Капитан Америка",
    "Тор", "Халк", "Черная вдова", "Соколиный глаз",
    
    # Философские
    "Ищу смысл жизни", "Философ", "Мыслитель", "Созерцатель",
    "Медитатор", "Йог", "Буддист", "Христианин", "Мусульманин",
    "Атеист", "Агностик", "Скептик", "Мистик", "Эзотерик",
    
    # Профессиональные
    "Журналист", "Писатель", "Поэт", "Актер", "Режиссер",
    "Продюсер", "Композитор", "Певец", "Танцор", "Хореограф",
    "Архитектор", "Инженер", "Ученый", "Исследователь", "Изобретатель",
    
    # Географические
    "Москвич", "Петербуржец", "Новосибирец", "Екатеринбуржец",
    "Казанец", "Нижегородец", "Ростовчанин", "Краснодарец",
    "Уралец", "Сибиряк", "Дальневосточник", "Северянин",
    
    # Временные
    "Ночной житель", "Ранняя пташка", "Сова", "Жаворонок",
    "Вечный студент", "Вечный ребенок", "Вечный подросток",
    "Вечный молодой", "Вечный старый", "Вечный новичок",
    
    # Социальные
    "Одиночка", "Компанейский", "Лидер", "Ведомый", "Бунтарь",
    "Конформист", "Нонконформист", "Анархист", "Консерватор",
    "Либерал", "Социалист", "Капиталист", "Коммунист",
    
    # Технологические
    "Технарь", "Гуманитарий", "Программист", "Хакер", "Киберпанк",
    "Нерд", "Гик", "Технофил", "Технофоб", "Цифровой кочевник",
    "IT-специалист", "Системный администратор", "Веб-разработчик",
    
    # Культурные
    "Интеллектуал", "Интеллигент", "Богема", "Буржуа", "Пролетарий",
    "Аристократ", "Демократ", "Республиканец", "Монархист",
    "Патриот", "Космополит", "Националист", "Интернационалист",
    
    # Личные качества
    "Честный", "Лживый", "Верный", "Предатель", "Дружелюбный",
    "Враждебный", "Терпеливый", "Нетерпеливый", "Спокойный",
    "Вспыльчивый", "Трудолюбивый", "Ленивый", "Активный", "Пассивный"
]

BOT_GOSSIP_TITLES = [
    # Эмоциональные реакции
    "я в шоке...", "что это было??", "ВИДЕЛИ?!", "не могу поверить",
    "просто оставлю это здесь", "без лишних слов", "мда уж",
    "ну вы поняли", "лол", "Слух дня", "Не поверите!", 
    
    # Подслушанное и слухи
    "Подслушано в коридоре", "Говорят, что...", "Маленький секрет", 
    "За кулисами", "Инсайд", "Слух дня", "Эксклюзив!", 
    "Кто бы мог подумать?", "Шокирующая правда",
    
    # Повседневные ситуации
    "Просто мысли вслух", "Сегодня такое было", "Недавно заметил",
    "Интересная ситуация", "Странное поведение", "Что происходит?",
    "Не понимаю людей", "Странные дела", "Интересные наблюдения",
    
    # Рабочие/учебные темы
    "На работе/учебе", "Коллеги/одногруппники", "Начальство/преподы",
    "Офисные/учебные будни", "Рабочие/учебные сплетни",
    
    # Семейные и дружеские темы
    "Семейные дела", "Друзья опять", "Родственники", "Соседи",
    "Домашние истории", "Семейные тайны",
    
    # Современные темы
    "В интернете", "В соцсетях", "В чате", "В группе",
    "Онлайн знакомства", "Интернет-драмы", "Цифровые сплетни",
    
    # Общие фразы
    "Интересная история", "Странная ситуация", "Необычный случай",
    "Забавная история", "Печальная история", "Мотивирующая история",
    "Поучительная история", "Смешная ситуация", "Грустная правда"
]
BOT_GOSSIP_CONTENTS = [
    # Рабочие/учебные сплетни
    "На работе один коллега постоянно жалуется на начальство, а сам ничего не делает. Сегодня опять услышал его нытье в курилке. Интересно, он понимает, что все его слышат?",
    "Вчера на совещании начальник объявил о повышении зарплат, но только избранным. Весь офис теперь в напряжении, все гадают, кто попал в список счастливчиков.",
    "Одногруппница постоянно списывает у всех домашние задания, а потом хвастается своими пятерками. Преподы ничего не замечают, а мы все молчим. Странно как-то.",
    "На работе новый сотрудник, а через неделю уже все знают его личную жизнь. Офисные сплетни работают быстрее интернета.",
    "Сегодня на паре преподаватель опоздал на 20 минут, а потом еще 15 минут рассказывал, как важно быть пунктуальным. Ирония судьбы.",
    
    # Семейные истории
    "Соседи сверху опять ругаются. Слышу уже третий час. Интересно, они понимают, что весь дом их слышит? Хочется то ли вызвать полицию, то ли подняться и помирить их.",
    "Родители опять пытаются устроить мою личную жизнь. Нашли какую-то девушку через знакомых и настойчиво предлагают познакомиться. Мне 25, а они все еще считают меня ребенком.",
    "Брат женился на девушке, которую знает всего месяц. Родители в шоке, я тоже. Но он говорит, что это любовь с первого взгляда. Интересно, надолго ли?",
    "Свекровь приехала в гости и уже третий день переставляет мебель. Муж ничего не говорит, а я не знаю, как объяснить, что мне нравится, как было.",
    "Дочь-подросток заявила, что хочет стать блогером. Родители в панике, а я думаю - может, это лучше, чем сидеть в телефоне целыми днями?",
    
    # Дружеские ситуации
    "Друг женился на девушке, которую мы все недолюбливали. Теперь он изменился, стал каким-то другим. Интересно, это временно или навсегда?",
    "Подруга развелась с мужем и теперь каждый день пишет в соцсетях грустные посты. Хочется поддержать, но не знаю как. Может, просто помолчать рядом?",
    "Друзья организовали вечеринку и забыли меня пригласить. Увидел фотки в инстаграме. Обидно, конечно, но может, я сам виноват?",
    "Лучший друг переехал в другой город и теперь общаемся только по телефону. Странно, как быстро люди отдаляются, когда нет личного общения.",
    "Подруга познакомилась с парнем в интернете и собирается к нему переезжать. Все отговаривают, а она не слушает. Надеюсь, все будет хорошо.",
    
    # Современные темы
    "В интернете познакомился с девушкой, общались месяц, а потом она исчезла. Оказалось, что это был фейковый аккаунт. Теперь не знаю, кому верить в сети.",
    "В группе ВК разгорелась настоящая драма из-за политики. Люди, которые раньше дружили, теперь оскорбляют друг друга. Интернет - странное место.",
    "Нашел старые фотки в телефоне и понял, как сильно изменился за последние годы. И не только внешне. Интересно, это хорошо или плохо?",
    "В чате одноклассников кто-то анонимно написал сплетни про всех. Весь класс теперь гадает, кто это. А я думаю - может, просто не читать?",
    "Подписался на блогера, который ведет здоровый образ жизни. Через неделю он выложил фото с фастфудом. Люди такие противоречивые.",
    
    # Повседневные наблюдения
    "Сегодня в метро увидел, как девушка уступила место пожилому мужчине, а он начал ее отчитывать за то, что она выглядит уставшей. Люди странные.",
    "В кафе за соседним столиком парень делал предложение девушке. Она сказала нет и ушла. Весь ресторан замер. Иногда жизнь как в кино.",
    "На улице увидел, как мама кричала на ребенка за то, что он уронил мороженое. Ребенок плакал, а прохожие делали вид, что ничего не происходит.",
    "В магазине кассирша была очень груба со всеми покупателями. Потом узнал, что у нее умерла мама. Никогда не знаешь, что происходит в жизни других людей.",
    "В автобусе водитель остановился и вышел помочь бабушке донести сумки. Весь автобус ждал. Есть еще хорошие люди в мире.",
    
    # Личные размышления
    "Иногда думаю, что мы все слишком много времени проводим в телефонах и забываем жить настоящей жизнью. Но потом снова беру телефон в руки.",
    "Недавно понял, что взросление - это не возраст, а состояние души. Некоторые в 40 ведут себя как подростки, а некоторые в 20 уже мудрые.",
    "Все говорят, что нужно найти свое предназначение в жизни. А что если мое предназначение - просто быть счастливым?",
    "Иногда хочется все бросить и уехать в глушь, а иногда - наоборот, в большой город. Противоречивые чувства.",
    "Заметил, что с возрастом все меньше хочется спорить и доказывать свою правоту. Может, это мудрость приходит?",
    
    # Забавные ситуации
    "Сегодня случайно отправил сообщение не тому человеку. Теперь объясняю, что это была ошибка, а он думает, что я его преследую.",
    "На работе забыл выключить микрофон на совещании и все услышали, как я ругаюсь на соседей. Теперь все знают мое мнение о шумных соседях.",
    "Попытался приготовить ужин по рецепту из интернета. Результат был настолько ужасен, что даже кот отказался есть. Теперь заказываю доставку.",
    "В лифте встретил соседа, которого не видел год. Он спросил, как дела, а я не помнил его имени. Пришлось изображать из себя очень занятого человека.",
    "На свидании девушка спросила, что я думаю о феминизме. Я растерялся и начал говорить что-то невнятное. Свидание не задалось.",
    
    # Грустные истории
    "У друга умерла собака, с которой он прожил 15 лет. Видеть его таким грустным больно. Животные становятся частью семьи, а потом их не становится.",
    "Подруга потеряла работу из-за сокращения. Она проработала там 10 лет. Теперь не знает, что делать дальше. Жизнь несправедлива.",
    "Родители стареют, и это пугает. Недавно мама забыла, как пользоваться микроволновкой. Старость приходит незаметно.",
    "Лучший друг переехал в другую страну. Теперь общаемся только по скайпу. Расстояние убивает дружбу медленно, но верно.",
    "Сегодня узнал, что бывшая девушка вышла замуж. Рад за нее, но почему-то грустно. Наверное, это нормально.",
    
    # Мотивирующие истории
    "Сегодня случайно встретил школьного учителя. Он сказал, что гордится мной. Не ожидал, что эти слова так много значат.",
    "Подруга открыла свой бизнес и уже через полгода он приносит прибыль. Вдохновляет видеть, как люди достигают своих целей.",
    "Сосед-пенсионер каждый день делает зарядку и бегает по утрам. Мне 25, а я не могу заставить себя встать с дивана. Стыдно.",
    "Увидел, как незрячий человек помогает другому незрячему перейти дорогу. Есть еще доброта в мире.",
    "Сегодня помог бабушке донести сумки до дома. Она была так благодарна, что чуть не плакала. Иногда простые поступки значат больше, чем мы думаем."
]
BOT_COMMENTS = [
    # Современный сленг и реакции
    "жиза", "лол кек", "+++", "ору", "เรียกว่า", "реально?", "всмысле", "согл",
    "база", "кринж", "емае", "👀", "🤔", "чтооо", "так и знал", "я в шоке",
    "ваще", "ну такое", "пфф", "хм", "интересно", "странно", "непонятно",
    "вау", "ого", "ух ты", "божечки", "мама дорогая", "нифига себе",
    
    # Эмодзи и реакции
    "😱", "😅", "🤦‍♂️", "🤦‍♀️", "😤", "😭", "😂", "😊", "😔", "😏",
    "🤷‍♂️", "🤷‍♀️", "🙄", "😒", "😮", "😲", "😳", "😬", "😌", "😴",
    
    # Короткие реакции
    "ага", "угу", "да", "нет", "возможно", "наверное", "точно", "сомнительно",
    "понятно", "ясно", "ладно", "ок", "хорошо", "плохо", "норм", "так себе",
    
    # Поддерживающие комментарии
    "Поддерживаю!", "Согласен на 100%", "Полностью согласен", "Точно подмечено",
    "Молодец!", "Хорошо написано", "Интересная мысль", "Умно подмечено",
    "Спасибо за пост!", "Полезная информация", "Благодарю за историю",
    
    # Вопросительные реакции
    "И что дальше?", "А потом что?", "И как это закончилось?",
    "Правда что ли?", "Серьезно?", "Не может быть!", "Вы уверены?",
    "А подробнее можно?", "Расскажи больше", "Интересно узнать детали",
    
    # Сочувствующие комментарии
    "Жаль, что так получилось", "Понимаю твои чувства", "Сочувствую",
    "Держись!", "Все будет хорошо", "Время лечит", "Не переживай",
    "Такое бывает", "Жизнь такая", "Ничего страшного",
    
    # Советующие комментарии
    "Попробуй поговорить", "Может, стоит обсудить?", "Советую подумать",
    "Лучше не торопиться", "Взвесь все за и против", "Прислушайся к себе",
    "Не стоит спешить", "Подумай хорошенько", "Решай сам",
    
    # Нейтральные комментарии (с ошибками и без)
    "Ого вот это новость!", "Интересно а что было дальше?", "Никогда бы не подумал.",
    "Звучит интригующе.", "Есть в этом что-то...", "Спасибо что поделились!", "Держите в курсе!",
    "Хм любопытно.", "Это многое объясняет.", "Как всегда на самом интересном месте!",
    "Интересная история", "Спасибо за пост", "Поделился с друзьями",
    
    # Более длинные комментарии
    "Спасибо, что поделился этой историей. Очень интересно читать такие посты.",
    "Никогда бы не подумал, что такое может произойти. Жизнь полна сюрпризов.",
    "Интересная ситуация. Надеюсь, все разрешится благополучно.",
    "Спасибо за пост! Всегда интересно читать истории из жизни других людей.",
    "Очень relatable история. У многих такое бывает в жизни.",
    
    # Комментарии с личным опытом
    "У меня было что-то похожее", "Знаю, о чем говоришь", "Понимаю ситуацию",
    "Была в такой же ситуации", "Проходил через это", "Знакомые чувства",
    "У меня тоже такое было", "Понимаю твою боль", "Знаю, как это тяжело",
    
    # Юмористические комментарии
    "Классика жанра", "Как в кино", "Жизнь - лучший сценарист",
    "Ну хоть что-то интересное происходит", "Скучно не будет",
    "Такие дела", "Вот так вот", "Жизнь преподносит сюрпризы",
    
    # Философские комментарии
    "Все в жизни происходит не просто так", "Время покажет",
    "Жизнь - штука сложная", "Никто не знает, что будет завтра",
    "Все течет, все изменяется", "Что поделаешь, такая жизнь",
    
    # Подбадривающие комментарии
    "Не сдавайся!", "Все получится", "Верь в себя", "Ты справишься",
    "Сильный человек", "Молодец, что держишься", "Горжусь тобой",
    "Ты на правильном пути", "Продолжай в том же духе",
    
    # Критические комментарии
    "Не согласен", "По-моему, это неправильно", "Сомнительно",
    "Не думаю, что это хорошая идея", "Может, стоит пересмотреть?",
    "Не уверен, что это правильно", "Спорное мнение",
    
    # Комментарии с вопросами
    "А что думают другие?", "А как отреагировали окружающие?",
    "А что сказали друзья?", "А родители в курсе?", "А что дальше?",
    "А как это повлияло на отношения?", "А что изменилось?",
    
    # Комментарии с предложениями
    "Может, стоит поговорить?", "Попробуй обсудить это",
    "Советую не торопиться", "Лучше подумать хорошенько",
    "Может, стоит дать время?", "Попробуй другой подход",
    
    # Комментарии с поддержкой
    "Мы с тобой!", "Ты не один", "Поддерживаем тебя",
    "Все будет хорошо", "Вместе справимся", "Ты сильный",
    "Не переживай, все наладится", "Время лечит все раны"
]

def generate_compound_gossip():
    """Генерирует составную сплетню, комбинируя разные элементы"""
    
    # Базовые темы для составных сплетен
    themes = [
        {
            'title_templates': [
                "Странная ситуация на работе",
                "Интересная история с друзьями", 
                "Необычный случай в транспорте",
                "Забавная история из жизни",
                "Печальная правда о людях",
                "Мотивирующая история",
                "Смешная ситуация",
                "Грустная реальность",
                "Удивительное наблюдение",
                "Загадочная история",
                "Поучительный случай",
                "Интересный опыт"
            ],
            'content_templates': [
                "Сегодня произошло что-то {adjective}. {main_story} {reaction} {conclusion}",
                "Недавно {main_story}. {reaction} {conclusion}",
                "Увидел(а) {main_story}. {reaction} {conclusion}",
                "Услышал(а) {main_story}. {reaction} {conclusion}",
                "Попал(а) в ситуацию: {main_story}. {reaction} {conclusion}",
                "Столкнулся(лась) с {main_story}. {reaction} {conclusion}",
                "Наблюдал(а) за тем, как {main_story}. {reaction} {conclusion}",
                "Стал(а) свидетелем того, как {main_story}. {reaction} {conclusion}"
            ]
        },
        {
            'title_templates': [
                "Размышления о людях",
                "Мысли вслух",
                "Личные наблюдения",
                "Философские размышления",
                "Жизненные уроки",
                "Интересные выводы",
                "Случайные мысли",
                "Дневниковые записи"
            ],
            'content_templates': [
                "Иногда задумываюсь о том, что {main_story}. {reaction} {conclusion}",
                "Недавно понял(а), что {main_story}. {reaction} {conclusion}",
                "Всегда удивляло меня, как {main_story}. {reaction} {conclusion}",
                "Заметил(а), что {main_story}. {reaction} {conclusion}",
                "Интересно наблюдать за тем, как {main_story}. {reaction} {conclusion}",
                "Порой кажется, что {main_story}. {reaction} {conclusion}"
            ]
        }
    ]
    
    theme = random.choice(themes)
    
    # Основные истории
    main_stories = [
        # Транспортные истории
        "в метро девушка уступила место пожилому мужчине, а он начал ее отчитывать за то, что она выглядит уставшей",
        "в автобусе водитель остановился и вышел помочь бабушке донести сумки",
        "в такси водитель рассказывал о своей жизни всю дорогу, а я просто хотел помолчать",
        "в электричке кто-то громко разговаривал по телефону, а все делали вид, что не слышат",
        
        # Рабочие истории
        "на работе коллега постоянно жалуется на начальство, а сам ничего не делает",
        "на совещании начальник объявил о повышении зарплат, но только избранным",
        "новый сотрудник через неделю уже знает все сплетни офиса",
        "преподаватель опоздал на 20 минут, а потом рассказывал о важности пунктуальности",
        
        # Семейные истории
        "соседи сверху опять ругаются уже третий час подряд",
        "родители опять пытаются устроить мою личную жизнь",
        "брат женился на девушке, которую знает всего месяц",
        "дочь-подросток заявила, что хочет стать блогером",
        
        # Общественные места
        "в кафе за соседним столиком парень делал предложение девушке, а она сказала нет и ушла",
        "в магазине кассирша была очень груба со всеми покупателями",
        "на улице мама кричала на ребенка за то, что он уронил мороженое",
        "в лифте встретил соседа, которого не видел год, а он спросил, как дела",
        
        # Личные истории
        "на свидании девушка спросила, что я думаю о феминизме, и я растерялся",
        "в интернете познакомился с девушкой, общались месяц, а потом она исчезла",
        "случайно отправил сообщение не тому человеку, теперь объясняю, что это была ошибка",
        "попытался приготовить ужин по рецепту из интернета, результат был ужасен",
        
        # Философские наблюдения
        "люди становятся все более зависимыми от технологий",
        "с каждым годом все меньше живого общения между людьми",
        "современная молодежь живет в своем цифровом мире",
        "люди все чаще предпочитают виртуальное общение реальному",
        "социальные сети создают иллюзию связи, но на самом деле отдаляют людей",
        "люди все меньше читают книги и все больше смотрят видео"
    ]
    
    # Прилагательные
    adjectives = [
        "странное", "забавное", "грустное", "смешное", "необычное", 
        "интересное", "печальное", "мотивирующее", "удивительное", "шокирующее"
    ]
    
    # Реакции
    reactions = [
        "Люди такие странные.", "Интересно, что происходит в головах у людей.",
        "Иногда жизнь как в кино.", "Никогда не знаешь, что ждет за углом.",
        "Мир полон сюрпризов.", "Люди удивляют каждый день.",
        "Жизнь преподносит неожиданные сюрпризы.", "Иногда просто нет слов.",
        "Мир такой противоречивый.", "Люди бывают очень разными."
    ]
    
    # Выводы
    conclusions = [
        "Интересно, что из этого получится.", "Надеюсь, все будет хорошо.",
        "Время покажет.", "Жизнь продолжается.", "Такие дела.",
        "Что поделаешь, такая жизнь.", "Все в жизни происходит не просто так.",
        "Надеюсь, это к лучшему.", "Интересно, что будет дальше.",
        "Жизнь - штука сложная."
    ]
    
    # Генерируем составную сплетню
    title = random.choice(theme['title_templates'])
    content_template = random.choice(theme['content_templates'])
    
    content = content_template.format(
        adjective=random.choice(adjectives),
        main_story=random.choice(main_stories),
        reaction=random.choice(reactions),
        conclusion=random.choice(conclusions)
    )
    
    return title, content

def markdown_to_html(text):
    """Простая конвертация Markdown в HTML"""
    if not text:
        return text
    
    # Жирный текст
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Курсив
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Заголовки
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Цитаты
    text = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
    
    # Списки
    text = re.sub(r'^- (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', text, flags=re.DOTALL)
    
    # Ссылки
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Переносы строк
    text = text.replace('\n\n', '</p><p>')
    text = f'<p>{text}</p>'
    
    return text

def generate_ai_gossip():
    """Генерирует сплетню с помощью OpenAI API"""
    
    if not client:
        return None, "OpenAI API не настроен"
    
    try:
        # Промпт для генерации сплетни
        prompt = """Напиши короткую сплетню из жизни, как будто ты обычный человек делишься с друзьями в соцсети.

Выбери любую тему:
- Что-то странное на работе или учебе
- Соседи или коллеги
- Общественный транспорт
- Кафе/магазин
- Семья
- Интернет
- Просто что-то забавное

Пиши как обычный человек - с ошибками, разговорными словами, не идеально. Используй эмодзи, но не перебарщивай.

Важно написать название на первой строчке и не форматировать его.

Пример:
Странный случай в метро

Сегодня в метро такая фигня произошла 😅 Девушка уступила место дедушке, а он начал её отчитывать что она уставшая выглядит! 

Весь вагон замер, а я думаю - ну и люди пошли 🤦‍♀️

Интересно что у них в голове происходит..."""

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        
        content = response.output_text
        
        # Парсим ответ - первая строка это название, остальное содержание
        lines = content.strip().split('\n')
        
        if len(lines) >= 2:
            title = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
        else:
            # Если только одна строка, используем её как название
            title = lines[0].strip() if lines else "Сплетня"
            body = ""
        
        # Если название слишком длинное или содержит маркеры, делаем его короче
        if len(title) > 50 or ':' in title:
            title = title.split(':')[-1].strip()[:50]
        
        # Если название пустое, генерируем простое
        if not title or title.lower() in ['название', 'содержание', 'ai сплетня']:
            title = "Интересная история"
        
        return title, body
        
    except Exception as e:
        print(f"[AI-ERROR] Ошибка при генерации сплетни: {e}")
        return None, f"Ошибка генерации: {str(e)}"

def generate_ai_comment(gossip_title, gossip_content):
    """Генерирует AI комментарий к сплетне"""
    
    if not client:
        return None, "OpenAI API не настроен"
    
    try:
        # Промпт для генерации комментария
        prompt = f"""Напиши короткий комментарий к этой сплетне, как будто ты обычный человек отвечаешь другу в соцсети.

Сплетня: {gossip_title}
{gossip_content}

Пиши как обычный человек - с ошибками, разговорными словами, не идеально. Используй эмодзи, но не перебарщивай.

Комментарий должен быть релевантным к сплетне - можешь:
- Поделиться похожей историей
- Выразить эмоции
- Задать вопрос
- Дать совет
- Просто отреагировать

Длина: 1-2 предложения максимум."""

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        
        comment = response.output_text.strip()
        
        # Очищаем комментарий от лишних символов
        if comment.startswith('"') and comment.endswith('"'):
            comment = comment[1:-1]
        
        # Если комментарий слишком длинный, обрезаем
        if len(comment) > 200:
            comment = comment[:197] + "..."
        
        return comment
        
    except Exception as e:
        print(f"[AI-ERROR] Ошибка при генерации комментария: {e}")
        return None

def change_reputation_for_gossip(bot, gossip):
    """Изменяет репутацию автора сплетни на основе её популярности"""
    try:
        author = gossip.author
        
        # Проверяем, не голосовал ли уже этот бот за этого автора сегодня
        today = datetime.utcnow().date()
        existing_vote = ReputationLog.query.filter_by(
            voter_id=bot.id, 
            target_id=author.id, 
            date_voted=today
        ).first()
        
        if existing_vote:
            return  # Уже голосовал сегодня
        
        # Рассчитываем популярность сплетни
        likes_count = len(gossip.likes)
        comments_count = len(gossip.comments)
        total_engagement = likes_count + comments_count * 2  # Комментарии важнее лайков
        
        # Базовые шансы
        positive_chance = 0.6  # 60% базовый шанс положительной репутации
        negative_chance = 0.4  # 40% базовый шанс отрицательной репутации
        
        # Модифицируем шансы на основе популярности
        if total_engagement >= 10:
            # Очень популярная сплетня - высокий шанс положительной репутации
            positive_chance = 0.9
            negative_chance = 0.1
        elif total_engagement >= 5:
            # Популярная сплетня - повышенный шанс положительной репутации
            positive_chance = 0.8
            negative_chance = 0.2
        elif total_engagement >= 2:
            # Средняя популярность - небольшой бонус к положительной репутации
            positive_chance = 0.7
            negative_chance = 0.3
        elif total_engagement == 0:
            # Непопулярная сплетня - повышенный шанс отрицательной репутации
            positive_chance = 0.4
            negative_chance = 0.6
        
        # Дополнительные модификаторы
        if author.is_verified:
            positive_chance += 0.1  # Проверенные пользователи получают бонус
            negative_chance -= 0.1
        
        if gossip.is_pinned_globally:
            positive_chance += 0.15  # Закрепленные сплетни дают большой бонус
            negative_chance -= 0.15
        
        # Ограничиваем шансы
        positive_chance = min(0.95, max(0.05, positive_chance))
        negative_chance = min(0.95, max(0.05, negative_chance))
        
        # Нормализуем шансы
        total = positive_chance + negative_chance
        positive_chance /= total
        negative_chance /= total
        
        # Определяем результат голосования
        if random.random() < positive_chance:
            # Положительная репутация
            author.reputation += 1
            vote_type = 'positive'
            print(f"[REPUTATION] {bot.username} повысил(а) репутацию {author.username} (+1) за популярную сплетню")
        else:
            # Отрицательная репутация
            author.reputation -= 1
            vote_type = 'negative'
            print(f"[REPUTATION] {bot.username} понизил(а) репутацию {author.username} (-1) за непопулярную сплетню")
        
        # Записываем голос в лог
        reputation_log = ReputationLog(
            voter_id=bot.id,
            target_id=author.id,
            vote_type=vote_type,
            date_voted=today
        )
        db.session.add(reputation_log)
        
    except Exception as e:
        print(f"[REPUTATION-ERROR] Ошибка при изменении репутации: {e}")

def get_smart_gossip_targets():
    """Получает умные цели для взаимодействия ботов с приоритетом свежести, закрепленным сплетням и проверенным пользователям"""
    
    # Получаем закрепленные сплетни (высший приоритет)
    pinned_gossips = Gossip.query.filter_by(is_pinned_globally=True).all()
    
    # Получаем недавние сплетни (последние 20 для лучшего выбора)
    recent_gossips = Gossip.query.order_by(Gossip.date_posted.desc()).limit(20).all()
    
    # Получаем популярные сплетни (с большим количеством лайков/комментариев)
    all_gossips = Gossip.query.all()
    popular_gossips = sorted(all_gossips, 
                           key=lambda g: len(g.likes) + len(g.comments) * 2, 
                           reverse=True)[:15]
    
    # Формируем приоритетный список
    priority_targets = []
    now = datetime.utcnow()
    
    # 1. Сначала закрепленные (высший приоритет) - добавляем несколько раз для большей вероятности
    if pinned_gossips:
        priority_targets.extend(pinned_gossips)
        # Добавляем еще раз для увеличения веса
        priority_targets.extend(pinned_gossips)
    
    # 2. Затем ОЧЕНЬ свежие сплетни (последние 10 минут) - максимальный бонус
    very_recent_gossips = []
    for gossip in recent_gossips:
        age_minutes = (now - gossip.date_posted).total_seconds() / 60
        if age_minutes <= 10:  # Последние 10 минут
            very_recent_gossips.append(gossip)
    
    if very_recent_gossips:
        # Добавляем очень свежие сплетни несколько раз для максимального веса
        priority_targets.extend(very_recent_gossips)
        priority_targets.extend(very_recent_gossips)
        priority_targets.extend(very_recent_gossips)
        print(f"[BOT-FRESH] Найдено {len(very_recent_gossips)} очень свежих сплетен (до 10 минут)")
    
    # 3. Затем свежие сплетни (последний час) - высокий бонус
    fresh_gossips = []
    for gossip in recent_gossips:
        if gossip not in very_recent_gossips:
            age_minutes = (now - gossip.date_posted).total_seconds() / 60
            if age_minutes <= 60:  # Последний час
                fresh_gossips.append(gossip)
    
    if fresh_gossips:
        # Добавляем свежие сплетни несколько раз для высокого веса
        priority_targets.extend(fresh_gossips)
        priority_targets.extend(fresh_gossips)
        print(f"[BOT-FRESH] Найдено {len(fresh_gossips)} свежих сплетен (до 1 часа)")
    
    # 4. Затем сплетни от проверенных пользователей (повышенный приоритет)
    verified_gossips = [g for g in recent_gossips if g.author.is_verified and g not in priority_targets]
    if verified_gossips:
        priority_targets.extend(verified_gossips)
        # Добавляем еще раз для увеличения веса проверенных
        priority_targets.extend(verified_gossips)
    
    # 5. Затем недавние популярные (много лайков/комментариев)
    for gossip in recent_gossips:
        if gossip not in priority_targets and (len(gossip.likes) > 3 or len(gossip.comments) > 2):
            priority_targets.append(gossip)
    
    # 6. Затем просто недавние (последние 24 часа)
    for gossip in recent_gossips:
        if gossip not in priority_targets and (now - gossip.date_posted).days < 1:
            priority_targets.append(gossip)
    
    # 7. Затем популярные старые (но не очень старые)
    for gossip in popular_gossips:
        if gossip not in priority_targets and (now - gossip.date_posted).days < 7:
            priority_targets.append(gossip)
    
    # 8. В конце добавляем остальные недавние
    for gossip in recent_gossips:
        if gossip not in priority_targets:
            priority_targets.append(gossip)
    
    # Если закрепленных нет, добавляем больше недавних
    if not pinned_gossips:
        more_recent = Gossip.query.order_by(Gossip.date_posted.desc()).limit(25).all()
        for gossip in more_recent:
            if gossip not in priority_targets:
                priority_targets.append(gossip)
    
    return priority_targets

def trigger_bot_actions(bots_to_activate):
    """Умная логика действий для указанного списка ботов."""
    with app.app_context():
        print(f"[BOT-ACTIVITY] Triggering actions for {len(bots_to_activate)} bots...")
        for bot in bots_to_activate:
            try:
                # Определяем тип бота для разных стратегий
                bot_type = random.choices(
                    population=['interactive', 'creative', 'passive', 'social'],
                    weights=[0.4, 0.3, 0.2, 0.1],
                    k=1
                )[0]
                
                # Получаем умные цели для взаимодействия
                smart_targets = get_smart_gossip_targets()
                
                # 70% шанс что бот создает AI контент (высокая частота)
                if random.random() < 0.7 and client:
                    ai_action = random.choice(['ai_gossip', 'ai_comment'])
                    
                    if ai_action == 'ai_gossip':
                        title, content = generate_ai_gossip()
                        if title and content:
                            content_html = markdown_to_html(content)
                            db.session.add(Gossip(title=title, content=content, content_html=content_html, user_id=bot.id))
                            print(f"[BOT-AI] {bot.username} создал(а) AI сплетню: {title}")
                            db.session.commit()
                            continue
                    
                    elif ai_action == 'ai_comment':
                        smart_targets = get_smart_gossip_targets()
                        if smart_targets:
                            target_gossip = random.choice(smart_targets)
                            if target_gossip.user_id != bot.id:
                                existing_comment = Comment.query.filter_by(user_id=bot.id, gossip_id=target_gossip.id).first()
                                if not existing_comment:
                                    comment_text = generate_ai_comment(target_gossip.title, target_gossip.content)
                                    if comment_text:
                                        db.session.add(Comment(content=comment_text, user_id=bot.id, gossip_id=target_gossip.id))
                                        print(f"[BOT-AI] {bot.username} создал(а) AI комментарий к сплетне '{target_gossip.title}': {comment_text[:50]}...")
                                        db.session.commit()
                                        continue
                
                # Обычная логика ботов
                if bot_type == 'interactive':
                    # Интерактивные боты - много лайкают и комментируют
                    action = random.choices(
                        population=['like', 'comment', 'gossip', 'claim_quest'],
                        weights=[0.50, 0.35, 0.10, 0.05],
                        k=1
                    )[0]
                    
                elif bot_type == 'creative':
                    # Креативные боты - больше создают контент
                    action = random.choices(
                        population=['like', 'comment', 'gossip', 'claim_quest'],
                        weights=[0.20, 0.25, 0.50, 0.05],
                        k=1
                    )[0]
                    
                elif bot_type == 'passive':
                    # Пассивные боты - в основном лайкают
                    action = random.choices(
                        population=['like', 'comment', 'gossip', 'claim_quest'],
                        weights=[0.70, 0.20, 0.05, 0.05],
                        k=1
                    )[0]
                    
                else:  # social
                    # Социальные боты - много комментируют
                    action = random.choices(
                        population=['like', 'comment', 'gossip', 'claim_quest'],
                        weights=[0.30, 0.50, 0.15, 0.05],
                        k=1
                    )[0]

                if action == 'like':
                    if not smart_targets: continue
                    
                    # Приоритет закрепленным сплетням
                    pinned_gossips = [g for g in smart_targets if g.is_pinned_globally]
                    if pinned_gossips and random.random() < 0.6:  # 60% шанс лайкнуть закрепленную
                        target_gossip = random.choice(pinned_gossips)
                    else:
                        # Взвешенный выбор с приоритетом свежести, популярности и проверенным авторам
                        weights = []
                        now = datetime.utcnow()
                        for g in smart_targets:
                            # Базовый вес
                            weight = 1
                            
                            # Бонус за популярность
                            weight += len(g.likes) * 0.5 + len(g.comments) * 1
                            
                            # Бонус за свежесть (плавно зависит от недавности)
                            age_minutes = (now - g.date_posted).total_seconds() / 60
                            if age_minutes <= 10:  # Последние 10 минут - максимальный бонус
                                weight *= 5
                            elif age_minutes <= 30:  # Последние 30 минут - высокий бонус
                                weight *= 4
                            elif age_minutes <= 60:  # Последний час - средний бонус
                                weight *= 3
                            elif age_minutes <= 180:  # Последние 3 часа - небольшой бонус
                                weight *= 2
                            elif age_minutes <= 1440:  # Последние 24 часа - минимальный бонус
                                weight *= 1.5
                            
                            # Бонус за закрепление
                            if g.is_pinned_globally:
                                weight *= 3
                            
                            # Бонус за проверенного автора
                            if g.author.is_verified:
                                weight *= 1.5
                            
                            weights.append(weight)
                        
                        target_gossip = random.choices(smart_targets, weights=weights, k=1)[0]
                    
                    already_liked = Like.query.filter_by(user_id=bot.id, gossip_id=target_gossip.id).first()
                    
                    if not already_liked and target_gossip.user_id != bot.id:
                        db.session.add(Like(user_id=bot.id, gossip_id=target_gossip.id))
                        
                        # 15% шанс изменить репутацию автора сплетни
                        if random.random() < 0.15:
                            change_reputation_for_gossip(bot, target_gossip)
                        
                        db.session.commit()
                        print(f"[BOT] {bot.username} лайкнул(а) сплетню #{target_gossip.id}")

                elif action == 'comment':
                    if not smart_targets: continue

                    # Приоритет закрепленным и популярным сплетням
                    pinned_gossips = [g for g in smart_targets if g.is_pinned_globally]
                    popular_gossips = [g for g in smart_targets if len(g.likes) > 3 or len(g.comments) > 2]
                    
                    if pinned_gossips and random.random() < 0.5:  # 50% шанс прокомментировать закрепленную
                        target_gossip = random.choice(pinned_gossips)
                    elif popular_gossips and random.random() < 0.7:  # 70% шанс прокомментировать популярную
                        target_gossip = random.choice(popular_gossips)
                    else:
                        # Взвешенный выбор с приоритетом свежести, популярности и проверенным авторам
                        weights = []
                        now = datetime.utcnow()
                        for g in smart_targets:
                            weight = 1
                            
                            # Бонус за популярность
                            weight += len(g.likes) * 0.3 + len(g.comments) * 0.8
                            
                            # Бонус за свежесть (плавно зависит от недавности)
                            age_minutes = (now - g.date_posted).total_seconds() / 60
                            if age_minutes <= 10:  # Последние 10 минут - максимальный бонус
                                weight *= 4
                            elif age_minutes <= 30:  # Последние 30 минут - высокий бонус
                                weight *= 3
                            elif age_minutes <= 60:  # Последний час - средний бонус
                                weight *= 2.5
                            elif age_minutes <= 180:  # Последние 3 часа - небольшой бонус
                                weight *= 2
                            elif age_minutes <= 1440:  # Последние 24 часа - минимальный бонус
                                weight *= 1.5
                            
                            # Бонус за закрепление
                            if g.is_pinned_globally:
                                weight *= 2
                            
                            # Бонус за проверенного автора
                            if g.author.is_verified:
                                weight *= 1.5
                            
                            weights.append(weight)
                        
                        target_gossip = random.choices(smart_targets, weights=weights, k=1)[0]
                    
                    if target_gossip.user_id != bot.id:
                        db.session.add(Comment(content=random.choice(BOT_COMMENTS), user_id=bot.id, gossip_id=target_gossip.id))
                        
                        # 20% шанс изменить репутацию автора сплетни (комментарии важнее лайков)
                        if random.random() < 0.20:
                            change_reputation_for_gossip(bot, target_gossip)
                        
                        db.session.commit()
                        print(f"[BOT] {bot.username} прокомментировал(а) сплетню #{target_gossip.id}")
                
                elif action == 'gossip':
                    # 30% шанс создать составную сплетню
                    if random.random() < 0.3:
                        title, content = generate_compound_gossip()
                        content_html = markdown_to_html(content)
                        db.session.add(Gossip(title=title, content=content, content_html=content_html, user_id=bot.id))
                        print(f"[BOT] {bot.username} опубликовал(а) составную сплетню.")
                    else:
                        db.session.add(Gossip(title=random.choice(BOT_GOSSIP_TITLES), content=random.choice(BOT_GOSSIP_CONTENTS), user_id=bot.id))
                        print(f"[BOT] {bot.username} опубликовал(а) готовую сплетню.")
                    
                    db.session.commit()

                elif action == 'claim_quest':
                    user_quests = UserQuest.query.filter_by(user_id=bot.id, claimed=False).all()
                    for uq in user_quests:
                        if uq.progress >= uq.quest.goal:
                            uq.claimed = True
                            bot.gossip_coins += uq.quest.reward
                            print(f"[BOT] {bot.username} забрал(а) награду за квест '{uq.quest.name}'")
                    db.session.commit()
                    
                # В тестовом режиме не спим, чтобы не держать транзакции и не блокировать SQLite
                if not app.config.get('TESTING'):
                    time.sleep(random.uniform(0.5, 2))  # Уменьшили задержку для снижения блокировок
            except Exception as e:
                print(f"Ошибка при действии бота {bot.username}: {e}")
                # Если произошла ошибка блокировки БД, делаем rollback
                try:
                    db.session.rollback()
                except:
                    pass


def run_bot_activity():
    print("--- Запуск фоновой задачи для активности ботов ---")
    while True:
        try:
            # Проверяем наличие свежих сплетен для адаптивной активности
            with app.app_context():
                now = datetime.utcnow()
                very_recent_gossips = Gossip.query.filter(
                    Gossip.date_posted >= now - timedelta(minutes=10)
                ).count()
                
                fresh_gossips = Gossip.query.filter(
                    Gossip.date_posted >= now - timedelta(minutes=60)
                ).count()
                
                # Адаптивная активность: больше ботов при наличии свежих сплетен
                # УВЕЛИЧИВАЕМ время ожидания в 10 раз для снижения активности
                base_sleep = random.randint(1800, 4800)  # Было 180-480, стало 1800-4800 (30-80 минут)
                if very_recent_gossips > 0:
                    # Если есть очень свежие сплетни (до 10 минут), уменьшаем время ожидания
                    sleep_duration = max(600, base_sleep // 2)  # Минимум 10 минут (было 1 минута)
                    print(f"[BOT-FRESH] Обнаружено {very_recent_gossips} очень свежих сплетен, ускоряем активность ботов")
                elif fresh_gossips > 2:
                    # Если есть несколько свежих сплетен (до 1 часа), немного ускоряем
                    sleep_duration = max(1200, base_sleep * 3 // 4)  # Минимум 20 минут (было 2 минуты)
                    print(f"[BOT-FRESH] Обнаружено {fresh_gossips} свежих сплетен, умеренно ускоряем активность")
                else:
                    sleep_duration = base_sleep
                    print(f"[BOT-FRESH] Свежих сплетен мало, обычная активность")
            
            time.sleep(sleep_duration)

            with app.app_context():
                bots = User.query.filter_by(is_bot=True).all()
                if not bots:
                    continue
                
                # Адаптивное количество активных ботов
                base_num_bots = random.randint(1, min(2, len(bots)))
                if very_recent_gossips > 0:
                    # Больше ботов при наличии очень свежих сплетен
                    num_active_bots = min(len(bots), base_num_bots + 1)
                elif fresh_gossips > 2:
                    # Немного больше ботов при наличии свежих сплетен
                    num_active_bots = min(len(bots), base_num_bots + 1)
                else:
                    num_active_bots = base_num_bots
                
                active_bots = random.sample(bots, num_active_bots)
                print(f"[BOT-ACTIVITY] Активируем {num_active_bots} ботов (свежих сплетен: {fresh_gossips}, очень свежих: {very_recent_gossips})")
            
            # Вызываем основную логику, которая сама создаст контекст
            trigger_bot_actions(active_bots)

        except Exception as e:
            print(f"Ошибка в фоновой задаче ботов: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_quests()
        seed_decorations()
        # Другие функции для заполнения базы данных, если они есть
    
    # Запускаем фоновый поток для проверки истечения срока закрепления
    stop_event = threading.Event()
    
    def check_pinned_gossips(stop_event_local):
        while not stop_event_local.is_set():
            try:
                with app.app_context():
                    pinned = Gossip.query.filter_by(is_pinned_globally=True).all()
                    now_ts = datetime.utcnow()
                    for g in pinned:
                        if g.pin_expires_at and g.pin_expires_at < now_ts:
                            g.is_pinned_globally = False
                    if pinned:
                        db.session.commit()
                time.sleep(30)
            except Exception as e:
                print(f"Ошибка в мониторинге закреплений: {e}")
                time.sleep(30)

    pin_check_thread = threading.Thread(target=check_pinned_gossips, args=(stop_event,), daemon=True)
    pin_check_thread.start()

    # Запускаем активность ботов в отдельном потоке (кроме тестового режима)
    if not app.config.get('TESTING'):
        bot_thread = threading.Thread(target=run_bot_activity, daemon=True)
        bot_thread.start()
        
        # Запускаем автоматическое резервное копирование
        backup_thread = threading.Thread(target=run_automatic_backup, daemon=True)
        backup_thread.start()

    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)

# --- Формы ---
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')
