let activeChatId = null;

async function loadChats() {
  const res = await fetch('/api/chats');
  const chats = await res.json();
  const list = document.getElementById('chat-list');
  list.innerHTML = '';
  chats.forEach(chat => {
    const li = document.createElement('li');
    li.textContent = chat.title;
    li.className = chat.id === activeChatId ? 'active' : '';
    li.onclick = () => openChat(chat.id);
    list.appendChild(li);
  });
  if (!activeChatId && chats.length) openChat(chats[0].id);
}

async function openChat(id) {
  activeChatId = id;
  const res = await fetch(`/api/chats/${id}`);
  const chat = await res.json();
  const messagesEl = document.getElementById('messages');
  messagesEl.innerHTML = '';
  chat.messages.forEach(m => addMessage(m.role, m.content));
  messagesEl.scrollTop = messagesEl.scrollHeight;
  loadChats();
}

function addMessage(role, content) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = content;
  document.getElementById('messages').appendChild(div);
}

document.getElementById('new-chat-btn').onclick = async () => {
  const res = await fetch('/api/chats', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
  const chat = await res.json();
  await loadChats();
  await openChat(chat.id);
};

document.getElementById('chat-form').onsubmit = async (e) => {
  e.preventDefault();
  const input = document.getElementById('message-input');
  const status = document.getElementById('status');
  const content = input.value.trim();
  if (!content || !activeChatId) return;
  addMessage('user', content);
  input.value = '';
  status.textContent = 'Gerando resposta...';
  try {
    const res = await fetch(`/api/chat/${activeChatId}/messages`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ content })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro desconhecido');
    addMessage('assistant', data.assistant_message.content);
    await loadChats();
  } catch (err) {
    addMessage('assistant', `Erro: ${err.message}`);
  }
  status.textContent = '';
  const messagesEl = document.getElementById('messages');
  messagesEl.scrollTop = messagesEl.scrollHeight;
};

loadChats();
