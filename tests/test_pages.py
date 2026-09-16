from .conftest import authenticate

PUBLIC_PAGES = ('/', '/about', '/contact', '/login', '/register')
PROTECTED_PAGES = ('/finance', '/invoice', '/optimizer.html',
                   '/exports', '/saved', '/imports', '/profile')


def test_public_pages_render(client):
    for path in PUBLIC_PAGES:
        r = client.get(path)
        assert r.status_code == 200, f'{path} should render (got {r.status_code})'


def test_protected_pages_render_when_authed(client):
    authenticate(client, 'renderuser')
    for path in PROTECTED_PAGES:
        r = client.get(path)
        assert r.status_code == 200, \
            f'{path} should render when authed (got {r.status_code}: {r.get_data(as_text=True)[:200]})'