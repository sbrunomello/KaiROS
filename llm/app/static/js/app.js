let activeChatId = null;
let modelCapabilities = { image_models: [], image_models_free: [], image_models_paid: [], video_input_models: [], video_generation_models: [], models: [], default_image_model: '' };
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

function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatInlineMarkdown(line) {
  let html = escapeHtml(line);
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  return html;
}

// Renderização básica de Markdown para melhorar legibilidade de respostas do LLM.
function renderMessageContent(content) {
  const raw = String(content || '').replace(/\r\n/g, '\n');
  const codeBlocks = [];
  const tokenized = raw.replace(/```([\w-]+)?\n([\s\S]*?)```/g, (_match, language, snippet) => {
    const langClass = language ? ` class="language-${escapeHtml(language)}"` : '';
    const code = `<pre><code${langClass}>${escapeHtml(snippet.trimEnd())}</code></pre>`;
    codeBlocks.push(code);
    return `@@CODE_BLOCK_${codeBlocks.length - 1}@@`;
  });

  const lines = tokenized.split('\n');
  const chunks = [];
  let listBuffer = [];

  const flushList = () => {
    if (!listBuffer.length) return;
    chunks.push(`<ul>${listBuffer.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join('')}</ul>`);
    listBuffer = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    if (trimmed.startsWith('@@CODE_BLOCK_')) {
      flushList();
      chunks.push(trimmed);
      return;
    }

    const listMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (listMatch) {
      listBuffer.push(listMatch[1]);
      return;
    }

    flushList();
    chunks.push(`<p>${formatInlineMarkdown(trimmed)}</p>`);
  });
  flushList();

  return chunks.join('').replace(/@@CODE_BLOCK_(\d+)@@/g, (_full, idx) => codeBlocks[Number(idx)] || '');
}

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

function addMessage(role, content) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = renderMessageContent(content);
  const messages = document.getElementById('messages');
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

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
    modelCapabilities = {
      models: [], image_models: [], image_models_free: [], image_models_paid: [],
      video_input_models: [], video_generation_models: [], default_image_model: ''
    };
  }

  renderImageModelCatalog();
  hydrateImageModelInput();

  const defaultInput = document.getElementById('default_image_model');
  if (!defaultInput.value && modelCapabilities.default_image_model) {
    defaultInput.value = modelCapabilities.default_image_model;
  }
}

function hydrateImageModelInput() {
  const input = document.getElementById('image-model-input');
  const suggestionList = document.getElementById('image-model-suggestions');
  if (!input || !suggestionList) return;

  const safeDefaults = ['bytedance-seed/seedream-4.5'];
  const catalogModels = modelCapabilities.image_models || [];
  const ids = [...new Set([...safeDefaults, ...catalogModels.map((m) => m.id).filter(Boolean)])];
  const configuredDefault = (document.getElementById('default_image_model')?.value || '').trim();
  const preferredModel = configuredDefault || modelCapabilities.default_image_model || safeDefaults[0];

  suggestionList.innerHTML = ids.map((modelId) => `<option value="${modelId}"></option>`).join('');
  if (!input.value.trim()) input.value = preferredModel;
}

function renderImageModelCatalog() {
  const holder = document.getElementById('image-model-catalog');
  if (!holder) return;

  const free = modelCapabilities.image_models_free || [];
  const paid = modelCapabilities.image_models_paid || [];

  const listHtml = (models, freeBadge) => {
    if (!models.length) return '<li>Nenhum modelo</li>';
    return models.map((m) => `<li><code>${m.id}</code>${freeBadge ? ' <span class="badge-free">FREE</span>' : ' <span class="badge-paid">PAGO</span>'} <span class="badge-info">IMAGE</span></li>`).join('');
  };

  holder.innerHTML = `
    <div class="model-group">
      <h4>Modelos free</h4>
      <ul>${listHtml(free, true)}</ul>
    </div>
    <div class="model-group">
      <h4>Modelos pagos</h4>
      <ul>${listHtml(paid, false)}</ul>
    </div>
  `;
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


function selectedImageMode() {
  const el = document.querySelector('input[name="image-mode"]:checked');
  return el ? el.value : 'text_to_image';
}

function renderInputPreview(file) {
  const holder = document.getElementById('image-input-preview');
  if (!holder) return;
  if (!file) { holder.innerHTML = ''; return; }
  const objectUrl = URL.createObjectURL(file);
  holder.innerHTML = `<img src="${objectUrl}" alt="preview" class="generated-image" />`;
}

async function loadImageHistory() {
  try {
    const data = await fetchJson(apiUrl('/api/history/multimodal'), { headers: usernameHeaders() });
    const imageItems = data.filter((item) => item.item_type === 'image_generation');
    const holder = document.getElementById('image-history');
    if (!holder) return;
    holder.innerHTML = imageItems.map((item) => `<div class="history-item"><strong>${item.model_name}</strong> - ${item.prompt}<br/><small>${item.metadata_json}</small><br/>${item.asset_url ? `<img src="${item.asset_url}" class="generated-image" alt="hist"/>` : ''}</div>`).join('') || '<p>Nenhum histórico.</p>';
  } catch (_e) {
    // histórico opcional
  }
}

async function generateImage() {
  const prompt = document.getElementById('image-prompt').value.trim();
  const mode = selectedImageMode();
  const imageFile = document.getElementById('image-input-file').files[0];
  if (!prompt) {
    setStatus('image-status', 'Digite um prompt para gerar imagem.');
    return;
  }
  if (mode === 'image_to_image' && !imageFile) {
    setStatus('image-status', 'Adicione uma imagem para usar o modo imagem para imagem.');
    return;
  }

  const button = document.getElementById('generate-image-btn');
  button.disabled = true;
  setStatus('image-status', 'Gerando imagem...');

  try {
    const selectedModel = document.getElementById('image-model-input').value.trim();
    if (!selectedModel) throw new Error('Informe um modelo de imagem para continuar.');

    const form = new FormData();
    form.append('prompt', prompt);
    form.append('model', selectedModel);
    form.append('mode', mode);
    if (imageFile) form.append('image', imageFile);

    const data = await fetchJson(apiUrl('/api/generate-image'), {
      method: 'POST',
      headers: { ...usernameHeaders() },
      body: form,
    });
    const holder = document.getElementById('image-result');
    holder.innerHTML = `
      <img src="${data.image_url}" alt="imagem gerada" class="generated-image" />
      <p>${data.text || ''}</p>
      <p><strong>Modo:</strong> ${data.mode} | <strong>Modelo:</strong> ${data.model} | <strong>Tipo:</strong> ${data.mime_type} | <strong>Tamanho:</strong> ${data.size_bytes} bytes</p>
      <a href="${data.image_url}" target="_blank">Abrir</a> | <a href="${data.image_url}" download>Download</a>
    `;
    setStatus('image-status', 'Imagem gerada com sucesso.');
    await loadImageHistory();
  } catch (e) {
    setStatus('image-status', `Erro: ${e.message}`);
  } finally {
    button.disabled = false;
  }
}

async function analyzeVideo() {
  setStatus('video-status', 'Analisando vídeo...');
  const file = document.getElementById('video-file').files[0];
  if (!file) { setStatus('video-status', 'Selecione um vídeo.'); return; }
  const form = new FormData();
  form.append('prompt', document.getElementById('video-prompt').value.trim());
  // Usa exclusivamente o modelo configurado na aba de configurações.
  const configuredVideoModel = (document.getElementById('default_video_analysis_model').value || '').trim();
  if (!configuredVideoModel) { setStatus('video-status', 'Defina o "Modelo padrão vídeo análise" na aba Configurações.'); return; }
  form.append('model', configuredVideoModel);
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
document.getElementById('default_image_model').addEventListener('input', () => {
  const imageModelInput = document.getElementById('image-model-input');
  const configuredDefault = document.getElementById('default_image_model').value.trim();
  if (imageModelInput && configuredDefault) imageModelInput.value = configuredDefault;
});
document.getElementById('refresh-models-btn').onclick = loadCapabilities;
document.getElementById('generate-image-btn').onclick = generateImage;
document.getElementById('image-input-file').onchange = (e) => renderInputPreview(e.target.files[0]);
document.getElementById('remove-image-btn').onclick = () => { const input = document.getElementById('image-input-file'); input.value = ''; renderInputPreview(null); };
document.getElementById('analyze-video-btn').onclick = analyzeVideo;

(function init() {
  const username = getStoredUsername();
  document.getElementById('username-input').value = username;
  activeChatId = restoreActiveChatId(username);
  initTabs();
  loadSettings().then(loadCapabilities);
  loadChats();
  loadImageHistory();
})();
