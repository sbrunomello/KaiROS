async function loadSettings() {
  const res = await fetch('/api/settings');
  const data = await res.json();
  Object.entries(data).forEach(([k, v]) => {
    const el = document.getElementById(k);
    if (!el) return;
    if (k === 'persist_multimodal_history') el.value = String(v);
    else el.value = v ?? '';
  });
}

document.getElementById('settings-form').onsubmit = async (e) => {
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
  const res = await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  document.getElementById('settings-status').textContent = res.ok ? 'Salvo com sucesso.' : 'Erro ao salvar.';
};

loadSettings();
