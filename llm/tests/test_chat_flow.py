def test_chat_flow_and_persistence(client):
    create = client.post('/api/chats', json={})
    assert create.status_code == 200
    chat_id = create.json()['id']

    send = client.post(f'/api/chat/{chat_id}/messages', json={'content': 'Olá teste'})
    assert send.status_code == 200
    body = send.json()
    assert body['assistant_message']['content'].startswith('Mock resposta:')

    detail = client.get(f'/api/chats/{chat_id}')
    assert detail.status_code == 200
    messages = detail.json()['messages']
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[1]['role'] == 'assistant'
