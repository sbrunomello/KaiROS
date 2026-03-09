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

  const videoModelInput = document.getElementById('video-model-input');
  if (videoModelInput && !videoModelInput.value.trim()) {
    videoModelInput.value = (document.getElementById('default_video_analysis_model')?.value || "").trim() || 'nvidia/nemotron-nano-12b-v2-vl:free';
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

const BOOLEAN_SELECT_FIELDS = new Set(['persist_multimodal_history']);
const BOOLEAN_CHECKBOX_FIELDS = new Set(['image_edit_enabled', 'video_enable_vision']);

function setSettingsFieldValue(field, value) {
  const el = document.getElementById(field);
  if (!el) return;

  if (BOOLEAN_CHECKBOX_FIELDS.has(field)) {
    el.checked = Boolean(value);
    return;
  }

  if (BOOLEAN_SELECT_FIELDS.has(field)) {
    el.value = String(Boolean(value));
    return;
  }

  el.value = value ?? '';
}

function getSettingsFieldValue(field) {
  const el = document.getElementById(field);
  if (!el) return undefined;

  if (BOOLEAN_CHECKBOX_FIELDS.has(field)) return el.checked;
  if (BOOLEAN_SELECT_FIELDS.has(field)) return el.value === 'true';
  if (el.type === 'number') return el.value === '' ? undefined : Number(el.value);
  return el.value;
}

async function loadSettings() {
  const data = await fetchJson('/api/settings');
  Object.entries(data).forEach(([field, value]) => setSettingsFieldValue(field, value));
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    openrouter_api_key: getSettingsFieldValue('openrouter_api_key') ?? '',
    groq_api_key: getSettingsFieldValue('groq_api_key') ?? '',
    huggingface_api_key: getSettingsFieldValue('huggingface_api_key') ?? '',
    chat_provider: getSettingsFieldValue('chat_provider') ?? 'groq',
    chat_fallback_provider: getSettingsFieldValue('chat_fallback_provider') ?? 'openrouter',
    speech_provider: getSettingsFieldValue('speech_provider') ?? 'groq',
    vision_provider: getSettingsFieldValue('vision_provider') ?? 'groq',
    image_gen_provider: getSettingsFieldValue('image_gen_provider') ?? 'openrouter',
    image_edit_provider: getSettingsFieldValue('image_edit_provider') ?? 'openrouter',
    video_analysis_mode: getSettingsFieldValue('video_analysis_mode') ?? 'legacy',
    model_name: getSettingsFieldValue('model_name') ?? 'openrouter/auto',
    chat_model_name: getSettingsFieldValue('chat_model_name') ?? 'openrouter/auto',
    speech_model_name: getSettingsFieldValue('speech_model_name') ?? 'whisper-large-v3-turbo',
    vision_model_name: getSettingsFieldValue('vision_model_name') ?? 'llama-3.2-11b-vision-preview',
    default_image_model: getSettingsFieldValue('default_image_model') ?? 'bytedance-seed/seedream-4.5',
    openrouter_default_image_model: getSettingsFieldValue('openrouter_default_image_model') ?? 'bytedance-seed/seedream-4.5',
    hf_default_image_model: getSettingsFieldValue('hf_default_image_model') ?? 'black-forest-labs/FLUX.1-schnell',
    image_edit_model_name: getSettingsFieldValue('image_edit_model_name') ?? '',
    default_video_analysis_model: getSettingsFieldValue('default_video_analysis_model') ?? 'nvidia/nemotron-nano-12b-v2-vl:free',
    default_video_generation_model: getSettingsFieldValue('default_video_generation_model') ?? '',
    whisper_cpp_binary_path: getSettingsFieldValue('whisper_cpp_binary_path') ?? '',
    whisper_cpp_model_path: getSettingsFieldValue('whisper_cpp_model_path') ?? '',
    ffmpeg_binary_path: getSettingsFieldValue('ffmpeg_binary_path') ?? 'ffmpeg',
    image_edit_enabled: getSettingsFieldValue('image_edit_enabled') ?? false,
    video_enable_vision: getSettingsFieldValue('video_enable_vision') ?? false,
    video_frame_sample_seconds: getSettingsFieldValue('video_frame_sample_seconds') ?? 5,
    temperature: getSettingsFieldValue('temperature') ?? 0.7,
    system_prompt: getSettingsFieldValue('system_prompt') ?? 'Você é uma assistente útil, objetiva e confiável.',
    assistant_name: getSettingsFieldValue('assistant_name') ?? 'Kai',
    http_referer: getSettingsFieldValue('http_referer') ?? '',
    x_title: getSettingsFieldValue('x_title') ?? '',
    request_timeout_seconds: getSettingsFieldValue('request_timeout_seconds') ?? 25,
    max_video_upload_mb: getSettingsFieldValue('max_video_upload_mb') ?? 20,
    persist_multimodal_history: getSettingsFieldValue('persist_multimodal_history') ?? true,
  };

  try {
    await fetchJson('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setStatus('settings-status', 'Salvo com sucesso.');
  } catch (e2) {
    setStatus('settings-status', `Erro ao salvar: ${e2.message}`);
  }
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


function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function renderVideoPreview(file) {
  const holder = document.getElementById('video-file-preview');
  if (!holder) return;
  if (!file) {
    holder.innerHTML = '<p>Nenhum vídeo anexado.</p>';
    return;
  }
  holder.innerHTML = `
    <p><strong>Nome:</strong> ${file.name}</p>
    <p><strong>Tamanho:</strong> ${formatBytes(file.size)}</p>
    <p><strong>MIME:</strong> ${file.type || '-'} </p>
  `;
}

async function loadVideoHistory() {
  try {
    const data = await fetchJson(apiUrl('/api/history/multimodal'), { headers: usernameHeaders() });
    const videoItems = data.filter((item) => item.item_type === 'video_analysis');
    const holder = document.getElementById('video-history');
    if (!holder) return;
    holder.innerHTML = videoItems.map((item) => `
      <div class="history-item">
        <p><strong>${item.model_name}</strong> - ${item.prompt}</p>
        <p>${item.response_text || ''}</p>
        <small>${item.metadata_json || ''}</small>
      </div>
    `).join('') || '<p>Nenhum histórico.</p>';
  } catch (_e) {
    // histórico opcional
  }
}

function copyVideoResult() {
  const text = document.getElementById('video-result-text')?.textContent || '';
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => setStatus('video-status', 'Resposta copiada.'));
}

async function analyzeVideo() {
  const button = document.getElementById('analyze-video-btn');
  const file = document.getElementById('video-file').files[0];
  const prompt = document.getElementById('video-prompt').value.trim();
  const model = document.getElementById('video-model-input').value.trim() || 'nvidia/nemotron-nano-12b-v2-vl:free';
  const reasoningEnabled = document.getElementById('video-reasoning-toggle').checked;

  if (!file) { setStatus('video-status', 'Adicione um vídeo para análise.'); return; }
  if (!prompt) { setStatus('video-status', 'Digite um prompt de análise.'); return; }

  const form = new FormData();
  form.append('prompt', prompt);
  form.append('model', model);
  form.append('reasoning_enabled', String(reasoningEnabled));
  form.append('video_file', file);

  button.disabled = true;
  setStatus('video-status', 'Analisando vídeo...');

  try {
    const data = await fetchJson(apiUrl('/api/analyze-video'), { method: 'POST', headers: { ...usernameHeaders() }, body: form });
    document.getElementById('video-result').innerHTML = `
      <p id="video-result-text">${escapeHtml(data.result || '')}</p>
      <p><strong>Modelo:</strong> ${escapeHtml(data.model || model)}</p>
      <p><strong>Reasoning:</strong> ${data.reasoning_enabled ? 'ativo' : 'desligado'}</p>
      <button id="copy-video-result-btn" type="button">Copiar resposta</button>
    `;
    document.getElementById('copy-video-result-btn')?.addEventListener('click', copyVideoResult);
    setStatus('video-status', 'Análise concluída.');
    await loadVideoHistory();
  } catch (e) {
    setStatus('video-status', `Erro: ${e.message}`);
  } finally {
    button.disabled = false;
  }
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
document.getElementById('video-file').onchange = (e) => renderVideoPreview(e.target.files[0]);
document.getElementById('remove-video-btn').onclick = () => { const input = document.getElementById('video-file'); input.value = ''; renderVideoPreview(null); };
document.getElementById('analyze-video-btn').onclick = analyzeVideo;

(function init() {
  const username = getStoredUsername();
  document.getElementById('username-input').value = username;
  activeChatId = restoreActiveChatId(username);
  initTabs();
  loadSettings().then(loadCapabilities);
  loadChats();
  loadImageHistory();
  loadVideoHistory();
  renderVideoPreview(null);
})();
