let activeChatId = null;

/**
 * Keep username selection local, no external auth (local-only multi-user isolation).
 */
function getStoredUsername() {
  return localStorage.getItem('kairos_username') || 'usuario1';
}

function setStoredUsername(username) {
  localStorage.setItem('kairos_username', username);
}

function getUsername() {
  const input = document.getElementById('username-input');
  return (input?.value || getStoredUsername()).trim();
}

function usernameHeaders() {
  return { 'X-Username': getUsername() };
}

function validateUsername(username) {
  return /^[a-zA-Z0-9_-]{3,32}$/.test(username);
}

async function loadChats() {
  const username = getUsername();
  const res = await fetch('/api/chats', { headers: usernameHeaders() });
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

  document.getElementById('active-user').textContent = `Usuário: ${username}`;

  if (!activeChatId && chats.length) {
    openChat(chats[0].id);
  }
}

async function openChat(id) {
  activeChatId = id;
  const res = await fetch(`/api/chats/${id}`, { headers: usernameHeaders() });
  if (!res.ok) {
    const body = await res.json();
    throw new Error(body.detail || 'Falha ao abrir conversa');
  }
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
  const username = getUsername();
  if (!validateUsername(username)) {
    alert("Username inválido. Use 3-32 caracteres com letras, números, '_' ou '-'.");
    return;
  }
  const res = await fetch('/api/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...usernameHeaders() },
    body: JSON.stringify({}),
  });
  const chat = await res.json();
  await loadChats();
  await openChat(chat.id);
};

document.getElementById('switch-user-btn').onclick = async () => {
  const username = getUsername();
  if (!validateUsername(username)) {
    alert("Username inválido. Use 3-32 caracteres com letras, números, '_' ou '-'.");
    return;
  }
  setStoredUsername(username);
  activeChatId = null;
  document.getElementById('messages').innerHTML = '';
  await loadChats();
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
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...usernameHeaders() },
      body: JSON.stringify({ content }),
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

(function initUserControls() {
  const usernameInput = document.getElementById('username-input');
  usernameInput.value = getStoredUsername();
})();

loadChats();
