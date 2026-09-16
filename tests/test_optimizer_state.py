import uuid

from blueprints import optimizer_state

from .conftest import authenticate


def _var(name):
    return {
        'name': name,
        'lowerBound': '0',
        'upperBound': '',
        'cost': '10',
        'profit': '2',
        'multiplier': '1',
    }


def _add_variable(client, name):
    data = _var(name)
    data['add_variable'] = 'yes'
    return client.post('/optimizer.html', data=data)


def _user_id(client):
    with client.session_transaction() as sess:
        return sess['user_id']


def _state(client, app_instance, user_id):
    with app_instance.app_context():
        return optimizer_state.load_state_for(user_id)


def _marker():
    return u'M' + uuid.uuid4().hex[:8]


def test_variables_stored_server_side_not_in_cookie(client, app_instance):
    authenticate(client, 'optuser')
    marker = _marker()
    _add_variable(client, marker)
    with client.session_transaction() as sess:
        assert 'optimizer_variables' not in sess
    state = _state(client, app_instance, _user_id(client))
    assert [v['name'] for v in state['variables']] == [marker]


def test_budget_persists_across_requests(client, app_instance):
    authenticate(client, 'optuser2')
    assert client.post('/optimizer.html', data={'budget': '500', 'update_budget': 'yes'}).status_code == 200
    state = _state(client, app_instance, _user_id(client))
    assert state['budget'] == 500


def test_clear_variables_resets_state(client, app_instance):
    authenticate(client, 'optuser3')
    marker = _marker()
    _add_variable(client, marker)
    assert client.post('/clear_variables').status_code == 302
    state = _state(client, app_instance, _user_id(client))
    assert state['variables'] == []
    assert state['budget'] is None
    body = client.get('/optimizer.html').get_data(as_text=True)
    assert marker not in body


def test_update_variable_persists(client, app_instance):
    authenticate(client, 'optuser4')
    marker = _marker()
    _add_variable(client, marker)
    resp = client.post('/update_variable', data=dict(_var(marker + 'B'), old_name=marker, name=marker + 'B'))
    assert resp.status_code == 200
    state = _state(client, app_instance, _user_id(client))
    assert [v['name'] for v in state['variables']] == [marker + 'B']


def test_state_is_isolated_between_users(client, app_instance):
    marker = _marker()
    authenticate(client, 'optuser5')
    _add_variable(client, marker)

    other_client = app_instance.test_client()
    authenticate(other_client, 'optuser6')
    body = other_client.get('/optimizer.html').get_data(as_text=True)
    assert marker not in body


def test_empty_state_is_not_shared(client, app_instance):
    authenticate(client, 'optuser7')
    marker = _marker()
    _add_variable(client, marker)

    other = app_instance.test_client()
    authenticate(other, 'optuser8')
    other_id = _user_id(other)
    with app_instance.app_context():
        assert optimizer_state.load_state_for(other_id)['variables'] == []
        assert optimizer_state.load_state_for(other_id)['variables'] == []