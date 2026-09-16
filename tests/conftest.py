import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from finance_core.storage import DataStorage as _DS

_orig_init = _DS.__init__


def _patched_init(self, storage_dir=None):
    if storage_dir is None:
        storage_dir = os.path.join('/tmp/profit_optimizer_tests', 'data')
    _orig_init(self, storage_dir)


_DS.__init__ = _patched_init

import pytest
from app import app


@pytest.fixture()
def app_instance(tmp_path):
    from app import _login_attempts

    app.config.update(TESTING=True)
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['OPTIMIZER_STATE_FOLDER'] = str(tmp_path / 'optimizer_state')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['EXPORT_FOLDER'] = str(tmp_path / 'exports')
    app.config['SAVED_FOLDER'] = str(tmp_path / 'saved')
    for name in ('uploads', 'exports', 'saved'):
        os.makedirs(str(tmp_path / name), exist_ok=True)
    yield app
    _login_attempts.clear()


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture()
def storage(tmp_path):
    from finance_core.storage import DataStorage
    return DataStorage(str(tmp_path / 'data'))


def register(client, username=None, password='pw123456'):
    import uuid

    if username is None:
        username = f'user_{uuid.uuid4().hex[:8]}'
    r = client.post('/register', data={
        'username': username,
        'password': password,
        'confirm_password': password,
    })
    if r.status_code != 302:
        username = f'{username}_{uuid.uuid4().hex[:8]}'
        r = client.post('/register', data={
            'username': username,
            'password': password,
            'confirm_password': password,
        })
    assert r.status_code == 302, 'registration should redirect after success'
    return username


def login(client, username, password='pw123456'):
    return client.post('/login', data={'username': username, 'password': password})


def authenticate(client, username='auth', password='pw123456'):
    real = register(client, username, password)
    client.post('/login', data={'username': real, 'password': password})
    return real