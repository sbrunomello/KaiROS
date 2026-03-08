def test_healthz(client):
    res = client.get('/healthz')
    assert res.status_code == 200
    assert res.json() == {'ok': True}


def test_status(client):
    res = client.get('/status')
    assert res.status_code == 200
    body = res.json()
    assert body['db'] == 'ok'
    assert body['settings_loaded'] is True
    assert body['model_configured']
