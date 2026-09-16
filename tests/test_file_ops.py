import csv
import io
import os

from .conftest import authenticate


def _seed_session(client, app_instance):
    from blueprints import optimizer_state

    authenticate(client, 'fileops')
    with client.session_transaction() as sess:
        user_id = sess['user_id']
    with app_instance.app_context():
        optimizer_state.save_state_for(user_id, variables=[
            {'name': 'Cake A', 'lowerBound': 0, 'upperBound': None, 'cost': 10.0, 'profit': 2.0, 'multiplier': 1},
            {'name': 'Cake B', 'lowerBound': 0, 'upperBound': None, 'cost': 5.0, 'profit': 3.0, 'multiplier': 2},
        ])


def test_export_writes_session_variables_to_csv(client, app_instance):
    _seed_session(client, app_instance)
    r = client.post('/export', data={'filename': 'vars', 'format': 'csv'})
    assert r.status_code == 302
    path = os.path.join(app_instance.config['EXPORT_FOLDER'], 'vars.csv')
    assert os.path.exists(path)
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert [row['name'] for row in rows] == ['Cake A', 'Cake B']


def test_import_round_trips_back_into_state(client, app_instance):
    from blueprints import optimizer_state

    _seed_session(client, app_instance)
    exported = client.post('/export', data={'filename': 'vars', 'format': 'csv'})
    assert exported.status_code == 302

    with client.session_transaction() as sess:
        user_id = sess['user_id']
    with app_instance.app_context():
        optimizer_state.clear_state_for(user_id)

    path = os.path.join(app_instance.config['EXPORT_FOLDER'], 'vars.csv')
    with open(path, 'rb') as f:
        r = client.post(
            '/import',
            data={'file': (io.BytesIO(f.read()), 'vars.csv')},
            content_type='multipart/form-data',
        )
    assert r.status_code == 302
    with app_instance.app_context():
        state = optimizer_state.load_state_for(user_id)
    names = [v['name'] for v in state['variables']]
    assert names == ['Cake A', 'Cake B']


def test_save_writes_json_to_saved_folder(client, app_instance):
    _seed_session(client, app_instance)
    r = client.post('/save', data={'filename': 'saved_vars', 'format': 'json'})
    assert r.status_code == 302
    path = os.path.join(app_instance.config['SAVED_FOLDER'], 'saved_vars.json')
    assert os.path.exists(path)
    import json
    with open(path) as f:
        data = json.load(f)
    assert [item['name'] for item in data] == ['Cake A', 'Cake B']


def test_save_results_without_session(client, app_instance):
    authenticate(client, 'resultsuser')
    r = client.post('/save_results', data={
        'filename': 'results',
        'format': 'csv',
        'data': '[{"name": "A", "units": 3, "cost": 120.0, "profit": 24.0}]',
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    path = os.path.join(app_instance.config['SAVED_FOLDER'], 'results.csv')
    assert os.path.exists(path)