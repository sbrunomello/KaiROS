let activeChatId = null;
let modelCapabilities = { image_models: [], video_input_models: [], video_generation_models: [], models: [] };
const ACTIVE_CHAT_KEY_PREFIX = 'kairos_active_chat_';

function getStoredUsername() { return localStorage.getItem('kairos_username') || 'usuario1'; }
function setStoredUsername(username) { localStorage.setItem('kairos_username', username); }
function getUsername() { return (document.getElementById('username-input')?.value || getStoredUsername()).trim(); }
function activeChatStorageKey(username) { return `${ACTIVE_CHAT_KEY_PREFIX}${username}`; }
function restoreActiveChatId(username) { const value = localStorage.getItem(activeChatStorageKey(username)); const parsed = Number.parseInt(value || '', 10); return Number.isNaN(parsed) ? null : parsed; }
function persistActiveChatId(username, chatId) { const key = activeChatStorageKey(username); if (chatId === null) localStorage.removeItem(key); else localStorage.setItem(key, String(chatId)); }
function usernameHeaders() { return { 'X-Username': getUsername() }; }
function apiUrl(path, username = getUsername()) { const url = new URL(path.startsWith('/') ? path : `/${path}`, window.location.origin); url.searchParams.set('username', username); return `${url.pathname}${url.search}`; }
function validateUsername(username) { return /^[a-zA-Z0-9_-]{3,32}$/.test(username); }

function setStatus(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Erro de requisição');
  return data;
}

async function loadChats({ shouldAutoOpen = true } = {}) {
  const username = getUsername();
  if (!validateUsername(username)) return;
  const chats = await fetchJson(apiUrl('/api/chats', username), { headers: usernameHeaders() });
  const list = document.getElementById('chat-list'); list.innerHTML = '';
  const availableIds = new Set(chats.map((c) => c.id));
  if (activeChatId === null) activeChatId = restoreActiveChatId(username);
  if (activeChatId !== null && !availableIds.has(activeChatId)) { activeChatId = null; persistActiveChatId(username, null); document.getElementById('messages').innerHTML = ''; }
  chats.forEach((chat) => { const li = document.createElement('li'); li.textContent = chat.title; li.className = chat.id === activeChatId ? 'active' : ''; li.onclick = () => openChat(chat.id); list.appendChild(li); });
  document.getElementById('active-user').textContent = `Usuário: ${username}`;
  if (shouldAutoOpen && !activeChatId && chats.length) await openChat(chats[0].id, { refreshList: false });
}

async function openChat(id, { refreshList = true } = {}) {
  activeChatId = id; persistActiveChatId(getUsername(), id);
  const chat = await fetchJson(apiUrl(`/api/chats/${id}`), { headers: usernameHeaders() });
  const messagesEl = document.getElementById('messages'); messagesEl.innerHTML = '';
  chat.messages.forEach((m) => addMessage(m.role, m.content));
  if (refreshList) await loadChats({ shouldAutoOpen: false });
}

function addMessage(role, content) { const div = document.createElement('div'); div.className = `msg ${role}`; div.textContent = content; document.getElementById('messages').appendChild(div); }

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach((x) => x.classList.remove('active'));
      document.querySelectorAll('.tab-section').forEach((x) => x.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

async function loadCapabilities() {
  try {
    modelCapabilities = await fetchJson('/api/models/capabilities');
  } catch (_e) {
    modelCapabilities = { models: [], image_models: [{ id: document.getElementById('default_image_model').value || 'google/gemini-3.1-flash-image-preview' }], video_input_models: [{ id: document.getElementById('default_video_analysis_model').value || 'google/gemini-2.5-pro' }], video_generation_models: [] };
  }
  fillModelSelect('image-model', modelCapabilities.image_models);
  fillModelSelect('video-analysis-model', modelCapabilities.video_input_models);
}

function fillModelSelect(id, models) {
  const el = document.getElementById(id); if (!el) return;
  el.innerHTML = '';
  models.forEach((m) => { const op = document.createElement('option'); op.value = m.id; op.textContent = m.name || m.id; el.appendChild(op); });
}

async function loadSettings() {
  const data = await fetchJson('/api/settings');
  Object.entries(data).forEach(([k, v]) => {
    const el = document.getElementById(k);
    if (!el) return;
    if (el.tagName === 'SELECT' && k === 'persist_multimodal_history') el.value = String(v);
    else el.value = v ?? '';
  });
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    openrouter_api_key: document.getElementById('openrouter_api_key').value,
    model_name: document.getElementById('model_name').value,
    default_image_model: document.getElementById('default_image_model').value,
    default_video_analysis_model: document.getElementById('default_video_analysis_model').value,
    default_video_generation_model: document.getElementById('default_video_generation_model').value,
    temperature: Number(document.getElementById('temperature').value || 0.7),
    system_prompt: document.getElementById('system_prompt').value,
    assistant_name: document.getElementById('assistant_name').value,
    http_referer: document.getElementById('http_referer').value,
    x_title: document.getElementById('x_title').value,
    request_timeout_seconds: Number(document.getElementById('request_timeout_seconds').value || 25),
    max_video_upload_mb: Number(document.getElementById('max_video_upload_mb').value || 20),
    persist_multimodal_history: document.getElementById('persist_multimodal_history').value === 'true',
  };
  try { await fetchJson('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); setStatus('settings-status', 'Salvo com sucesso.'); }
  catch (e2) { setStatus('settings-status', `Erro ao salvar: ${e2.message}`); }
}

async function generateImage() {
  setStatus('image-status', 'Gerando imagem...');
  try {
    const payload = { prompt: document.getElementById('image-prompt').value.trim(), model: document.getElementById('image-model').value };
    const data = await fetchJson(apiUrl('/api/generate-image'), { method: 'POST', headers: { 'Content-Type': 'application/json', ...usernameHeaders() }, body: JSON.stringify(payload) });
    const holder = document.getElementById('image-result');
    holder.innerHTML = `<img src="${data.image_url}" alt="imagem gerada" class="generated-image" /><p>${data.text || ''}</p><a href="${data.image_url}" target="_blank">Abrir</a> | <a href="${data.image_url}" download>Download</a>`;
    setStatus('image-status', 'Imagem gerada com sucesso.');
  } catch (e) { setStatus('image-status', `Erro: ${e.message}`); }
}

async function analyzeVideo() {
  setStatus('video-status', 'Analisando vídeo...');
  const file = document.getElementById('video-file').files[0];
  if (!file) { setStatus('video-status', 'Selecione um vídeo.'); return; }
  const form = new FormData();
  form.append('prompt', document.getElementById('video-prompt').value.trim());
  form.append('model', document.getElementById('video-analysis-model').value);
  form.append('video_file', file);
  try {
    const data = await fetchJson(apiUrl('/api/analyze-video'), { method: 'POST', headers: { ...usernameHeaders() }, body: form });
    document.getElementById('video-result').textContent = data.result;
    setStatus('video-status', 'Análise concluída.');
  } catch (e) { setStatus('video-status', `Erro: ${e.message}`); }
}

document.getElementById('new-chat-btn').onclick = async () => { const res = await fetchJson(apiUrl('/api/chats'), { method: 'POST', headers: { 'Content-Type': 'application/json', ...usernameHeaders() }, body: '{}' }); await loadChats(); await openChat(res.id); };
document.getElementById('switch-user-btn').onclick = async () => { const username = getUsername(); if (!validateUsername(username)) return alert('Username inválido'); setStoredUsername(username); activeChatId = restoreActiveChatId(username); document.getElementById('messages').innerHTML = ''; await loadChats(); };
document.getElementById('chat-form').onsubmit = async (e) => { e.preventDefault(); const input = document.getElementById('message-input'); const content = input.value.trim(); if (!content || !activeChatId) return; addMessage('user', content); input.value = ''; setStatus('status', 'Gerando resposta...'); try { const data = await fetchJson(apiUrl(`/api/chat/${activeChatId}/messages`), { method: 'POST', headers: { 'Content-Type': 'application/json', ...usernameHeaders() }, body: JSON.stringify({ content }) }); addMessage('assistant', data.assistant_message.content); await loadChats(); } catch (e2) { addMessage('assistant', `Erro: ${e2.message}`); } setStatus('status', ''); };
document.getElementById('settings-form').onsubmit = saveSettings;
document.getElementById('refresh-models-btn').onclick = loadCapabilities;
document.getElementById('generate-image-btn').onclick = generateImage;
document.getElementById('analyze-video-btn').onclick = analyzeVideo;

(function init() {
  const username = getStoredUsername();
  document.getElementById('username-input').value = username;
  activeChatId = restoreActiveChatId(username);
  initTabs();
  loadSettings().then(loadCapabilities);
  loadChats();
})();
