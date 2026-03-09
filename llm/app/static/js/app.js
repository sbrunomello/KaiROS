let activeChatId = null;
const ACTIVE_CHAT_KEY_PREFIX = 'kairos_active_chat_';

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

function activeChatStorageKey(username) {
  return `${ACTIVE_CHAT_KEY_PREFIX}${username}`;
}

function restoreActiveChatId(username) {
  const storedValue = localStorage.getItem(activeChatStorageKey(username));
  if (!storedValue) return null;

  const parsedId = Number.parseInt(storedValue, 10);
  return Number.isNaN(parsedId) ? null : parsedId;
}

function persistActiveChatId(username, chatId) {
  const key = activeChatStorageKey(username);
  if (chatId === null) {
    localStorage.removeItem(key);
    return;
  }
  localStorage.setItem(key, String(chatId));
}

function usernameHeaders() {
  return { 'X-Username': getUsername() };
}

function validateUsername(username) {
  return /^[a-zA-Z0-9_-]{3,32}$/.test(username);
}

async function loadChats({ shouldAutoOpen = true } = {}) {
  const username = getUsername();
  if (!validateUsername(username)) {
    document.getElementById('active-user').textContent = 'Usuário inválido';
    return;
  }

  const res = await fetch('/api/chats', { headers: usernameHeaders() });
  if (!res.ok) {
    throw new Error('Falha ao carregar conversas');
  }

  const chats = await res.json();
  const list = document.getElementById('chat-list');
  list.innerHTML = '';
  const availableIds = new Set(chats.map(chat => chat.id));

  if (activeChatId === null) {
    activeChatId = restoreActiveChatId(username);
  }
  if (activeChatId !== null && !availableIds.has(activeChatId)) {
    activeChatId = null;
    persistActiveChatId(username, null);
    document.getElementById('messages').innerHTML = '';
  }

  chats.forEach(chat => {
    const li = document.createElement('li');
    li.textContent = chat.title;
    li.className = chat.id === activeChatId ? 'active' : '';
    li.onclick = () => openChat(chat.id);
    list.appendChild(li);
  });

  document.getElementById('active-user').textContent = `Usuário: ${username}`;

  if (shouldAutoOpen && !activeChatId && chats.length) {
    await openChat(chats[0].id, { refreshList: false });
  }
}

async function openChat(id, { refreshList = true } = {}) {
  activeChatId = id;
  persistActiveChatId(getUsername(), id);

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
  if (refreshList) {
    await loadChats({ shouldAutoOpen: false });
  }
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
  activeChatId = restoreActiveChatId(username);
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
  const username = getStoredUsername();
  usernameInput.value = username;
  activeChatId = restoreActiveChatId(username);
})();

loadChats();
