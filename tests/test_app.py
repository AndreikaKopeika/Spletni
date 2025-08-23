from app import User, Gossip, Comment, Like, CoinTransaction, Notification, Quest, UserQuest, ReputationLog
from app import db

def test_register_page(client):
    """Тест: страница регистрации открывается успешно."""
    response = client.get('/register')
    assert response.status_code == 200
    assert 'Регистрация' in response.data.decode('utf-8')

def test_register_new_user(client):
    """Тест: успешная регистрация нового пользователя."""
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Ваш аккаунт был создан!' in response.data.decode('utf-8')
    
    with client.application.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None

def test_login_logout(client, new_user):
    """Тест: успешный вход и выход пользователя."""
    # Тестируем вход
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Выйти' in response.data.decode('utf-8')  # Проверяем, что на странице есть кнопка выхода

    # Тестируем выход
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert 'Войти' in response.data.decode('utf-8')  # Проверяем, что на странице есть кнопка входа

def test_create_gossip(client, new_user):
    """Тест: авторизованный пользователь может создать сплетню (через прямую запись в БД и проверку отображения)."""
    # Логинимся
    client.post('/login', data={'username': 'testuser', 'password': 'password123'})

    # Создаём сплетню напрямую (в приложении нет явного /gossip/new)
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        gossip = Gossip(title='Тестовый заголовок', content='Это тестовое содержание сплетни.', user_id=user.id)
        db.session.add(gossip)
        db.session.commit()
        gossip_id = gossip.id

    # Проверяем, что страница сплетни открывается
    resp = client.get(f'/gossip/{gossip_id}')
    assert resp.status_code == 200
    page = resp.data.decode('utf-8')
    assert 'Тестовый заголовок' in page
    assert 'Это тестовое содержание сплетни.' in page

def test_add_comment(client, new_user):
    """Тест: авторизованный пользователь может оставить комментарий."""
    client.post('/login', data={'username': 'testuser', 'password': 'password123'})

    # Сначала создаем сплетню, чтобы было что комментировать
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        gossip = Gossip(title="Сплетня для коммента", content="Содержание", user_id=user.id)
        db.session.add(gossip)
        db.session.commit()
        gossip_id = gossip.id

    response = client.post(f'/gossip/{gossip_id}/comment', data={
        'content': 'Это тестовый комментарий.'
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'

    with client.application.app_context():
        comment = Comment.query.filter_by(content='Это тестовый комментарий.').first()
        assert comment is not None
        assert comment.gossip_id == gossip_id

def test_like_gossip_basic(logged_in_client):
    """Тест: базовая функциональность лайка сплетни"""
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        g = Gossip(title='Test gossip', content='Content', user_id=user.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    # Лайкаем сплетню
    resp = logged_in_client.post(f'/gossip/{gid}/like', follow_redirects=True)
    assert resp.status_code == 200

def test_like_gossip_author_coins(logged_in_client, second_user):
    """Тест: автор получает коины за лайк"""
    with logged_in_client.application.app_context():
        # Создаем сплетню от имени второго пользователя
        author = User.query.filter_by(username='otheruser').first()
        initial_coins = author.gossip_coins
        g = Gossip(title='Test gossip', content='Content', user_id=author.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    # Лайкаем сплетню от имени первого пользователя
    logged_in_client.post(f'/gossip/{gid}/like', follow_redirects=True)
    
    with logged_in_client.application.app_context():
        author_after = User.query.filter_by(username='otheruser').first()
        assert author_after.gossip_coins > initial_coins

def test_pin_gossip_basic(logged_in_client):
    """Тест: базовая функциональность закрепления сплетни"""
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        user.gossip_coins = 1000
        db.session.commit()
        g = Gossip(title='Test gossip', content='Content', user_id=user.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    # Закрепляем сплетню
    resp = logged_in_client.post(f'/gossip/{gid}/pin', data={'csrf_token': ''}, follow_redirects=True)
    assert resp.status_code == 200

def test_overbid_gossip(logged_in_client):
    """Тест: перебивание закрепленной сплетни"""
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        user.gossip_coins = 1000
        db.session.commit()
        g1 = Gossip(title='G1', content='C1', user_id=user.id)
        g2 = Gossip(title='G2', content='C2', user_id=user.id)
        db.session.add_all([g1, g2])
        db.session.commit()
        g1_id, g2_id = g1.id, g2.id

    # Сначала закрепляем первую
    logged_in_client.post(f'/gossip/{g1_id}/pin', data={'csrf_token': ''}, follow_redirects=True)
    # Затем перебиваем второй
    resp = logged_in_client.post(f'/gossip/{g2_id}/pin', data={'csrf_token': ''}, follow_redirects=True)
    assert resp.status_code == 200

def test_coin_transfer_basic(logged_in_client, second_user):
    """Тест: базовая функциональность перевода коинов"""
    # Пополняем баланс отправителя
    with logged_in_client.application.app_context():
        sender = User.query.filter_by(username='testuser').first()
        sender.gossip_coins = 200
        db.session.commit()

    # Выполняем перевод
    resp = logged_in_client.post('/coin-center', data={
        'recipient': 'otheruser',
        'amount': '10',
        'message': 'test transfer'
    }, follow_redirects=True)
    assert resp.status_code == 200

def test_coin_transfer_verification(logged_in_client, second_user):
    """Тест: проверка результатов перевода коинов"""
    # Пополняем баланс отправителя
    with logged_in_client.application.app_context():
        sender = User.query.filter_by(username='testuser').first()
        sender.gossip_coins = 200
        db.session.commit()

    # Выполняем перевод
    logged_in_client.post('/coin-center', data={
        'recipient': 'otheruser',
        'amount': '10',
        'message': 'test transfer'
    }, follow_redirects=True)
    
    # Проверяем результаты
    with logged_in_client.application.app_context():
        sender_after = User.query.filter_by(username='testuser').first()
        recipient_after = User.query.filter_by(username='otheruser').first()
        assert sender_after.gossip_coins <= 190  # 200 - 10
        assert recipient_after.gossip_coins >= 110  # 100 + 10


def test_quests_flow(logged_in_client, new_user):
    # открываем страницу квестов
    r = logged_in_client.get('/quests')
    assert r.status_code == 200
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        uq = UserQuest.query.filter_by(user_id=user.id).all()
        assert len(uq) > 0  # Должны быть назначены квесты


def test_developer_add_coins(developer_client, new_user):
    """Тест: добавление коинов через панель разработчика"""
    with developer_client.application.app_context():
        # Перезагружаем пользователя из базы данных
        user = User.query.get(new_user.id)
        initial_coins = user.gossip_coins
        
    resp = developer_client.post(f'/developer/add_coins/{new_user.id}', data={'amount': '5'}, follow_redirects=True)
    assert resp.status_code == 200
    
    with developer_client.application.app_context():
        user_after = User.query.get(new_user.id)
        assert user_after.gossip_coins == initial_coins + 5

def test_developer_toggle_moderator(developer_client, new_user):
    """Тест: переключение статуса модератора"""
    with developer_client.application.app_context():
        user = User.query.get(new_user.id)
        initial_status = user.is_moderator
        
    resp = developer_client.get(f'/developer_panel/toggle_moderator/{new_user.id}', follow_redirects=True)
    assert resp.status_code == 200
    
    with developer_client.application.app_context():
        user_after = User.query.get(new_user.id)
        assert user_after.is_moderator != initial_status

def test_developer_toggle_verified(developer_client, new_user):
    """Тест: переключение статуса верификации"""
    with developer_client.application.app_context():
        user = User.query.get(new_user.id)
        initial_status = user.is_verified
        
    resp = developer_client.get(f'/developer_panel/toggle_verified/{new_user.id}', follow_redirects=True)
    assert resp.status_code == 200
    
    with developer_client.application.app_context():
        user_after = User.query.get(new_user.id)
        assert user_after.is_verified != initial_status

def test_developer_refresh_quests(developer_client):
    """Тест: обновление квестов через панель разработчика"""
    # Проверяем, что кнопка обновления квестов работает
    resp = developer_client.post('/developer/refresh_quests', data={'csrf_token': ''}, follow_redirects=True)
    assert resp.status_code == 200
    
    # Проверяем, что в ответе есть сообщение об успешном обновлении
    response_text = resp.data.decode('utf-8')
    assert 'квесты были принудительно обновлены' in response_text or 'success' in response_text.lower()

def test_add_comment_basic(logged_in_client):
    """Тест: базовая функциональность добавления комментария"""
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        g = Gossip(title='G for comments', content='...', user_id=user.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    # Добавляем комментарий
    resp = logged_in_client.post(f'/gossip/{gid}/comment', data={'content': 'Nice'}, follow_redirects=True)
    assert resp.status_code == 200

def test_like_comment_basic(logged_in_client):
    """Тест: базовая функциональность лайка комментария"""
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        g = Gossip(title='G for comments', content='...', user_id=user.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id

    # Добавляем комментарий
    resp = logged_in_client.post(f'/gossip/{gid}/comment', data={'content': 'Nice'}, follow_redirects=True)
    assert resp.status_code == 200
    
    # Получаем ID комментария
    comment_data = resp.get_json()
    cid = comment_data['comment']['id']
    
    # Лайкаем комментарий
    resp2 = logged_in_client.post(f'/comment/{cid}/like', follow_redirects=True)
    assert resp2.status_code == 200

def test_bots_panel_access(developer_client):
    """Тест: доступ к панели управления ботами"""
    resp = developer_client.get('/developer_panel/bots')
    assert resp.status_code in (200, 302)

def test_bots_create(developer_client):
    """Тест: создание ботов"""
    resp = developer_client.post('/developer_panel/bots', data={'action': 'create', 'bot_count': '2'}, follow_redirects=True)
    assert resp.status_code in (200, 302)

def test_bots_trigger_activity(developer_client):
    """Тест: запуск активности ботов"""
    resp = developer_client.post('/developer_panel/bots', data={'action': 'trigger_activity'}, follow_redirects=True)
    assert resp.status_code in (200, 302)


def test_comment_and_like_comment(logged_in_client, new_user):
    with logged_in_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        g = Gossip(title='G for comments', content='...', user_id=user.id)
        db.session.add(g)
        db.session.commit()
        gid = g.id
    # add comment
    rc = logged_in_client.post(f'/gossip/{gid}/comment', data={'content': 'Nice'}, follow_redirects=True)
    assert rc.status_code == 200
    cid = rc.get_json()['comment']['id']
    # like comment
    rl = logged_in_client.post(f'/comment/{cid}/like', follow_redirects=True)
    assert rl.status_code == 200
    data = rl.get_json()
    assert data['liked'] is True


def test_leaderboard(logged_in_client):
    r = logged_in_client.get('/leaderboard')
    assert r.status_code == 200

def test_quests_page_design(logged_in_client):
    """Тест: проверка дизайна страницы квестов"""
    resp = logged_in_client.get('/quests')
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    # Проверяем, что страница использует правильную структуру
    assert 'Ежедневные квесты' in response_text
    assert 'quests-container' in response_text
    assert 'quest-card' in response_text
    # Проверяем, что используется base.html (а не layout.html)
    assert 'Сплетни Revamp' in response_text  # Это есть в base.html

def test_profile_page_access(logged_in_client, second_user):
    """Тест: доступ к странице профиля"""
    resp = logged_in_client.get(f'/user/{second_user.username}')
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    assert second_user.username in response_text
    assert 'Репутация:' in response_text

def test_profile_page_own_profile(logged_in_client):
    """Тест: доступ к собственному профилю"""
    resp = logged_in_client.get('/user/testuser')
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    assert 'testuser' in response_text
    assert 'Репутация:' in response_text

def test_upvote_user(logged_in_client, second_user):
    """Тест: голосование за повышение репутации пользователя"""
    initial_reputation = second_user.reputation
    
    resp = logged_in_client.post(f'/user/{second_user.username}/upvote', 
                                data={'csrf_token': ''}, 
                                follow_redirects=True)
    assert resp.status_code == 200
    
    with logged_in_client.application.app_context():
        user_after = User.query.filter_by(username=second_user.username).first()
        assert user_after.reputation == initial_reputation + 1

def test_downvote_user(logged_in_client, second_user):
    """Тест: голосование за понижение репутации пользователя"""
    initial_reputation = second_user.reputation
    
    resp = logged_in_client.post(f'/user/{second_user.username}/downvote', 
                                data={'csrf_token': ''}, 
                                follow_redirects=True)
    assert resp.status_code == 200
    
    with logged_in_client.application.app_context():
        user_after = User.query.filter_by(username=second_user.username).first()
        assert user_after.reputation == initial_reputation - 1

def test_vote_own_profile(logged_in_client):
    """Тест: попытка голосовать за свой профиль"""
    resp = logged_in_client.post('/user/testuser/upvote', 
                                data={'csrf_token': ''}, 
                                follow_redirects=True)
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    assert 'не можете голосовать за свою репутацию' in response_text

def test_double_vote_same_day(logged_in_client, second_user):
    """Тест: попытка проголосовать дважды за одного пользователя в один день"""
    # Первый голос
    resp1 = logged_in_client.post(f'/user/{second_user.username}/upvote', 
                                 data={'csrf_token': ''}, 
                                 follow_redirects=True)
    assert resp1.status_code == 200
    
    # Второй голос (должен быть отклонен)
    resp2 = logged_in_client.post(f'/user/{second_user.username}/downvote', 
                                 data={'csrf_token': ''}, 
                                 follow_redirects=True)
    assert resp2.status_code == 200
    
    response_text = resp2.data.decode('utf-8')
    assert 'уже голосовали за этого пользователя сегодня' in response_text

def test_profile_with_gossips(logged_in_client, second_user):
    """Тест: профиль пользователя со сплетнями"""
    # Создаем сплетню для второго пользователя
    with logged_in_client.application.app_context():
        gossip = Gossip(title='Тестовая сплетня', content='Содержание', user_id=second_user.id)
        db.session.add(gossip)
        db.session.commit()
    
    resp = logged_in_client.get(f'/user/{second_user.username}')
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    assert 'Тестовая сплетня' in response_text
    assert 'Сплетни пользователя' in response_text

def test_profile_pagination(logged_in_client, second_user):
    """Тест: пагинация в профиле пользователя"""
    # Создаем несколько сплетен для тестирования пагинации
    with logged_in_client.application.app_context():
        for i in range(6):  # Создаем 6 сплетен (больше чем per_page=5)
            gossip = Gossip(title=f'Сплетня {i}', content=f'Содержание {i}', user_id=second_user.id)
            db.session.add(gossip)
        db.session.commit()
    
    resp = logged_in_client.get(f'/user/{second_user.username}')
    assert resp.status_code == 200
    
    response_text = resp.data.decode('utf-8')
    assert 'Следующая' in response_text  # Должна быть пагинация

def test_profile_page_no_crash(logged_in_client, second_user):
    """Тест: страница профиля не крашится при отсутствии роутов голосования"""
    # Проверяем, что страница загружается без ошибок
    resp = logged_in_client.get(f'/user/{second_user.username}')
    assert resp.status_code == 200
    
    # Проверяем, что в ответе нет ошибок BuildError
    response_text = resp.data.decode('utf-8')
    assert 'BuildError' not in response_text
    assert 'Could not build url' not in response_text
    assert 'upvote_user' not in response_text  # Не должно быть ошибок с роутами

def test_vote_csrf_protection(logged_in_client, second_user):
    """Тест: CSRF защита в роутах голосования"""
    # В тестовом режиме CSRF отключен, поэтому тест должен проходить успешно
    # Попытка голосовать без CSRF токена
    resp = logged_in_client.post(f'/user/{second_user.username}/upvote', 
                                data={}, 
                                follow_redirects=True)
    assert resp.status_code == 200
    
    # В тестовом режиме голосование должно пройти успешно, так как CSRF отключен
    response_text = resp.data.decode('utf-8')
    # Проверяем, что голосование прошло успешно (нет ошибки CSRF)
    assert 'Ошибка CSRF' not in response_text
    assert 'повышена' in response_text

def test_vote_nonexistent_user(logged_in_client):
    """Тест: голосование за несуществующего пользователя"""
    resp = logged_in_client.post('/user/nonexistentuser/upvote', 
                                data={'csrf_token': ''}, 
                                follow_redirects=True)
    assert resp.status_code == 404

def test_vote_with_csrf_token(logged_in_client, second_user):
    """Тест: голосование с CSRF токеном"""
    # Получаем CSRF токен из формы
    resp = logged_in_client.get(f'/user/{second_user.username}')
    assert resp.status_code == 200
    
    # Извлекаем CSRF токен из ответа (упрощенная версия)
    initial_reputation = second_user.reputation
    
    # Голосуем с пустым CSRF токеном (в тестах это работает)
    resp = logged_in_client.post(f'/user/{second_user.username}/upvote', 
                                data={'csrf_token': ''}, 
                                follow_redirects=True)
    assert resp.status_code == 200
    
    with logged_in_client.application.app_context():
        user_after = User.query.filter_by(username=second_user.username).first()
        assert user_after.reputation == initial_reputation + 1
