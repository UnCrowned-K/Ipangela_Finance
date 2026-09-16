import os

from .conftest import authenticate, login, register


def test_public_pages_open(client):
    for path in ('/', '/about', '/contact', '/login', '/register'):
        assert client.get(path).status_code == 200, path


def test_feature_pages_require_login(client):
    for path in ('/finance', '/invoice', '/optimizer.html', '/exports',
                 '/saved', '/imports', '/profile'):
        r = client.get(path)
        assert r.status_code == 302, path
        assert '/login' in r.headers.get('Location', ''), path


def test_api_requires_login(client):
    assert client.get('/api/finance/data').status_code == 401
    assert client.post('/api/finance/transaction', json={}).status_code == 401
    assert client.get('/api/finance/transaction/abc').status_code == 401


def test_full_login_flow(client):
    user = register(client, 'flowuser')
    r = login(client, user)
    assert r.status_code == 302
    assert r.headers.get('Location', '').endswith('/finance')
    with client.session_transaction() as sess:
        assert 'user_id' in sess
    assert client.get('/finance').status_code == 200


def test_wrong_password_rejected(client):
    user = register(client, 'wrongpw')
    assert login(client, user, 'nope').status_code == 200
    r = login(client, user)
    assert r.status_code == 302


def test_login_rate_limited_after_failures(client):
    user = register(client, 'ratelimit')
    from app import MAX_LOGIN_ATTEMPTS
    for _ in range(MAX_LOGIN_ATTEMPTS):
        client.post('/login', data={'username': user, 'password': 'bad'})
    r = login(client, user)
    assert r.status_code == 429
    assert client.get('/finance').status_code == 302


def test_download_traversal_blocked(client, app_instance, tmp_path):
    authenticate(client, 'dluser')
    up = app_instance.config['UPLOAD_FOLDER']
    ex = app_instance.config['EXPORT_FOLDER']
    sv = app_instance.config['SAVED_FOLDER']
    for folder in (up, ex, sv):
        with open(os.path.join(folder, 'real.csv'), 'w') as f:
            f.write('name,cost\nX,1\n')

    attacks = ['../real.csv', '../../config.py', '..%2f..%2fconfig.py',
               '....//....//config.py', 'config.py', 'app.py', '/etc/passwd',
               os.path.join('..', 'requirements.txt')]
    for route, folder in (('download_uploaded', up), ('download_file', ex), ('download_saved', sv)):
        r = client.get(f'/{route}/real.csv')
        assert r.status_code == 200, f'{route} legit download'
        body = r.get_data(as_text=True)
        assert 'name,cost' in body, f'{route} returns file content'
        for attack in attacks:
            assert client.get(f'/{route}/{attack}').status_code != 200, f'{route} leaked via {attack!r}'