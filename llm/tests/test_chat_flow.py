def test_chat_flow_and_persistence(client):
    headers = {'X-Username': 'usuario1'}

    create = client.post('/api/chats', json={}, headers=headers)
    assert create.status_code == 200
    chat_id = create.json()['id']

    send = client.post(f'/api/chat/{chat_id}/messages', json={'content': 'Olá teste'}, headers=headers)
    assert send.status_code == 200
    body = send.json()
    assert body['assistant_message']['content'].startswith('Mock resposta:')

    detail = client.get(f'/api/chats/{chat_id}', headers=headers)
    assert detail.status_code == 200
    messages = detail.json()['messages']
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[1]['role'] == 'assistant'


def test_chat_isolation_between_users(client):
    first_user = {'X-Username': 'usuario1'}
    second_user = {'X-Username': 'usuario2'}

    create = client.post('/api/chats', json={}, headers=first_user)
    assert create.status_code == 200
    chat_id = create.json()['id']

    list_second = client.get('/api/chats', headers=second_user)
    assert list_second.status_code == 200
    assert list_second.json() == []

    detail_second = client.get(f'/api/chats/{chat_id}', headers=second_user)
    assert detail_second.status_code == 404


def test_invalid_username_returns_422(client):
    response = client.get('/api/chats', headers={'X-Username': 'x'})
    assert response.status_code == 422
