def test_settings_read_write(client):
    original = client.get('/api/settings').json()
    assert original['model_name']

    payload = {
        'openrouter_api_key': 'abc123',
        'model_name': 'deepseek/deepseek-chat',
        'temperature': 0.3,
        'system_prompt': 'Seja objetivo.',
        'assistant_name': 'Nora',
        'http_referer': 'http://localhost',
        'x_title': 'KaiROS LLM'
    }
    res = client.put('/api/settings', json=payload)
    assert res.status_code == 200
    assert res.json()['model_name'] == 'deepseek/deepseek-chat'

    reloaded = client.get('/api/settings').json()
    assert reloaded['assistant_name'] == 'Nora'
