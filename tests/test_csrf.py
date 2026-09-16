import re
import uuid

import pytest

from app import create_app


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def csrf_app():
    app = create_app()
    app.config["TESTING"] = True
    return app


def _get_token(client, path="/register"):
    resp = client.get(path)
    m = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    assert m is not None, "csrf_token hidden input not rendered"
    return m.group(1)


def test_post_without_token_rejected(csrf_app):
    client = csrf_app.test_client()
    resp = client.post(
        "/register",
        data={
            "username": _unique("nu"),
            "password": "pw123456",
            "confirm_password": "pw123456",
        },
    )
    assert resp.status_code == 400


def test_post_with_form_token_accepted(csrf_app):
    client = csrf_app.test_client()
    token = _get_token(client)
    resp = client.post(
        "/register",
        data={
            "username": _unique("nu"),
            "password": "pw123456",
            "confirm_password": "pw123456",
            "csrf_token": token,
        },
    )
    assert resp.status_code == 302


def test_api_post_with_header_token_accepted(csrf_app):
    client = csrf_app.test_client()
    token = _get_token(client)
    resp = client.post(
        "/register",
        data={
            "username": _unique("nu"),
            "password": "pw123456",
            "confirm_password": "pw123456",
        },
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 302


def test_stale_token_rejected(csrf_app):
    client = csrf_app.test_client()
    _get_token(client)  # establishes the session token
    resp = client.post(
        "/register",
        data={
            "username": _unique("nu"),
            "password": "pw123456",
            "confirm_password": "pw123456",
            "csrf_token": "not-the-right-token",
        },
    )
    assert resp.status_code == 400