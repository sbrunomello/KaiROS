async function loadSettings() {
  const res = await fetch('/api/settings');
  const data = await res.json();
  Object.entries(data).forEach(([k,v]) => {
    const el = document.getElementById(k);
    if (el) el.value = v ?? '';
  });
}

document.getElementById('settings-form').onsubmit = async (e) => {
  e.preventDefault();
  const payload = {
    openrouter_api_key: document.getElementById('openrouter_api_key').value,
    model_name: document.getElementById('model_name').value,
    temperature: Number(document.getElementById('temperature').value || 0.7),
    system_prompt: document.getElementById('system_prompt').value,
    assistant_name: document.getElementById('assistant_name').value,
    http_referer: document.getElementById('http_referer').value,
    x_title: document.getElementById('x_title').value,
  };
  const res = await fetch('/api/settings', {
    method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
  });
  document.getElementById('settings-status').textContent = res.ok ? 'Salvo com sucesso.' : 'Erro ao salvar.';
};

loadSettings();
