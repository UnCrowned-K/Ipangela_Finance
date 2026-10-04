import json
import os

from .conftest import authenticate

PUBLIC_PAGES = ('/', '/about', '/contact', '/login', '/register')
PROTECTED_PAGES = ('/finance', '/invoice', '/optimizer.html',
                   '/exports', '/saved', '/imports', '/profile')

VALID_MESSAGE = {
    'name': 'Thandi Mokoena',
    'email': 'thandi@example.com',
    'subject': 'bug',
    'message': 'The budget field rejects cents, so I cannot enter R1500.50.',
}


def _store(app):
    return os.path.join(app.config['MESSAGE_FOLDER'], 'messages.json')


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


def test_contact_page_has_no_duplicate_ids(client):
    """A duplicated id makes getElementById return the wrong element, which
    silently unbinds the handler that was meant for the form."""
    import re

    html = client.get('/contact').get_data(as_text=True)
    ids = re.findall(r'\sid="([^"]+)"', html)
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, f'contact.html repeats these ids: {duplicates}'


def test_contact_form_posts_somewhere(client):
    """The form must not preventDefault into a void: it used to show a
    thank-you alert while discarding the message."""
    html = client.get('/contact').get_data(as_text=True)
    form = html.split('<form', 1)[1].split('>', 1)[0]
    assert 'action=' in form, 'the contact form should post to an endpoint'
    assert 'method="post"' in form.lower()


def test_contact_message_is_stored(client, app_instance):
    r = client.post('/contact', data=VALID_MESSAGE,
                    headers={'Accept': 'application/json'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['success'] is True

    with open(_store(app_instance), encoding='utf-8') as handle:
        stored = json.load(handle)
    assert len(stored) == 1
    assert stored[0]['email'] == VALID_MESSAGE['email']
    assert stored[0]['message'] == VALID_MESSAGE['message']
    assert stored[0]['received_at']


def test_contact_message_appends_rather_than_replaces(client, app_instance):
    for index in range(2):
        client.post('/contact', data={**VALID_MESSAGE,
                                      'message': f'Message number {index}'},
                    headers={'Accept': 'application/json'})
    with open(_store(app_instance), encoding='utf-8') as handle:
        stored = json.load(handle)
    assert len(stored) == 2, 'each message should be kept'


def test_contact_rejects_an_empty_submission(client, app_instance):
    r = client.post('/contact', data={}, headers={'Accept': 'application/json'})
    assert r.status_code == 400
    assert not os.path.exists(_store(app_instance)), \
        'a rejected message should not be written'


def test_contact_rejects_a_message_that_is_too_short(client, app_instance):
    r = client.post('/contact', data={**VALID_MESSAGE, 'message': 'hi'},
                    headers={'Accept': 'application/json'})
    assert r.status_code == 400
    assert not os.path.exists(_store(app_instance))


def test_contact_rejects_an_invalid_email(client, app_instance):
    r = client.post('/contact', data={**VALID_MESSAGE, 'email': 'not-an-email'},
                    headers={'Accept': 'application/json'})
    assert r.status_code == 400
    assert not os.path.exists(_store(app_instance))


def test_contact_falls_back_to_a_redirect_without_javascript(client, app_instance):
    """No JS: the plain POST still has to store the message and land somewhere."""
    r = client.post('/contact', data=VALID_MESSAGE)
    assert r.status_code == 302, 'a plain form post should redirect back'
    assert '/contact' in r.headers['Location']
    assert os.path.exists(_store(app_instance))


def test_contact_records_who_sent_it_when_signed_in(client, app_instance):
    authenticate(client, 'sender')
    client.post('/contact', data=VALID_MESSAGE,
                headers={'Accept': 'application/json'})
    with open(_store(app_instance), encoding='utf-8') as handle:
        stored = json.load(handle)
    assert stored[0]['user_id'], 'a signed-in sender should be recorded'