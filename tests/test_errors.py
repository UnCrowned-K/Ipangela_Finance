import pytest

from app import create_app


@pytest.fixture
def error_app():
    app = create_app()
    app.config["TESTING"] = True

    @app.route("/boom")
    def boom():
        raise RuntimeError("boom for tests")

    return app


def test_404_renders_html_page(error_app):
    client = error_app.test_client()
    resp = client.get("/definitely-not-a-page")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 404
    assert "404" in body
    assert "Page Not Found" in body


def test_404_api_returns_json(error_app):
    client = error_app.test_client()
    resp = client.get("/api/definitely-not-an-api")
    assert resp.status_code == 404
    payload = resp.get_json()
    assert payload["success"] is False
    assert payload["code"] == 404


def test_405_handled(error_app):
    resp = error_app.test_client().post("/")
    assert resp.status_code == 405


def test_500_renders_html_page(error_app):
    client = error_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
    resp = client.get("/boom")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 500
    assert "500" in body
    assert "Internal Server Error" in body


def test_500_api_returns_json(error_app):
    client = error_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
    resp = client.get("/boom", headers={"Accept": "application/json"})
    assert resp.status_code == 500
    payload = resp.get_json()
    assert payload["success"] is False
    assert payload["code"] == 500