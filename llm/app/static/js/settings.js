const BOOLEAN_SELECT_FIELDS = new Set(['persist_multimodal_history']);
const BOOLEAN_CHECKBOX_FIELDS = new Set(['image_edit_enabled', 'video_enable_vision']);

function setFieldValue(field, value) {
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

function getFieldValue(field) {
  const el = document.getElementById(field);
  if (!el) return undefined;

  if (BOOLEAN_CHECKBOX_FIELDS.has(field)) {
    return el.checked;
  }

  if (BOOLEAN_SELECT_FIELDS.has(field)) {
    return el.value === 'true';
  }

  if (el.type === 'number') {
    return el.value === '' ? undefined : Number(el.value);
  }

  return el.value;
}

async function loadSettings() {
  const res = await fetch('/api/settings');
  if (!res.ok) {
    document.getElementById('settings-status').textContent = 'Erro ao carregar configurações.';
    return;
  }

  const data = await res.json();
  Object.entries(data).forEach(([field, value]) => {
    setFieldValue(field, value);
  });
}

document.getElementById('settings-form').onsubmit = async (e) => {
  e.preventDefault();

  const payload = {
    openrouter_api_key: getFieldValue('openrouter_api_key') ?? '',
    groq_api_key: getFieldValue('groq_api_key') ?? '',
    huggingface_api_key: getFieldValue('huggingface_api_key') ?? '',
    cloudflare_api_token: getFieldValue('cloudflare_api_token') ?? '',
    cloudflare_account_id: getFieldValue('cloudflare_account_id') ?? '',
    together_api_key: getFieldValue('together_api_key') ?? '',
    deepinfra_api_key: getFieldValue('deepinfra_api_key') ?? '',
    chat_provider: getFieldValue('chat_provider') ?? 'groq',
    chat_fallback_provider: getFieldValue('chat_fallback_provider') ?? 'openrouter',
    speech_provider: getFieldValue('speech_provider') ?? 'groq',
    vision_provider: getFieldValue('vision_provider') ?? 'groq',
    vision_fallback_provider: getFieldValue('vision_fallback_provider') ?? '',
    image_gen_provider: getFieldValue('image_gen_provider') ?? 'openrouter',
    image_gen_fallback_provider: getFieldValue('image_gen_fallback_provider') ?? '',
    image_edit_provider: getFieldValue('image_edit_provider') ?? 'openrouter',
    image_edit_fallback_provider: getFieldValue('image_edit_fallback_provider') ?? '',
    video_analysis_mode: getFieldValue('video_analysis_mode') ?? 'legacy',
    model_name: getFieldValue('model_name') ?? 'openrouter/auto',
    chat_model_name: getFieldValue('chat_model_name') ?? 'openrouter/auto',
    speech_model_name: getFieldValue('speech_model_name') ?? 'whisper-large-v3-turbo',
    vision_model_name: getFieldValue('vision_model_name') ?? 'llama-3.2-11b-vision-preview',
    default_image_model: getFieldValue('default_image_model') ?? 'bytedance-seed/seedream-4.5',
    openrouter_default_image_model: getFieldValue('openrouter_default_image_model') ?? 'bytedance-seed/seedream-4.5',
    hf_default_image_model: getFieldValue('hf_default_image_model') ?? 'black-forest-labs/FLUX.1-schnell',
    cloudflare_default_chat_model: getFieldValue('cloudflare_default_chat_model') ?? '@cf/meta/llama-3.1-8b-instruct',
    cloudflare_default_vision_model: getFieldValue('cloudflare_default_vision_model') ?? '@cf/llava-hf/llava-1.5-7b-hf',
    cloudflare_default_image_model: getFieldValue('cloudflare_default_image_model') ?? '@cf/stabilityai/stable-diffusion-xl-base-1.0',
    together_default_chat_model: getFieldValue('together_default_chat_model') ?? 'meta-llama/Llama-3.1-8B-Instruct-Turbo',
    together_default_vision_model: getFieldValue('together_default_vision_model') ?? 'meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo',
    together_default_image_model: getFieldValue('together_default_image_model') ?? 'black-forest-labs/FLUX.1-schnell',
    deepinfra_default_chat_model: getFieldValue('deepinfra_default_chat_model') ?? 'meta-llama/Meta-Llama-3.1-8B-Instruct',
    deepinfra_default_vision_model: getFieldValue('deepinfra_default_vision_model') ?? 'meta-llama/Llama-3.2-11B-Vision-Instruct',
    deepinfra_default_image_model: getFieldValue('deepinfra_default_image_model') ?? 'black-forest-labs/FLUX.1-schnell',
    hf_image_edit_endpoint: getFieldValue('hf_image_edit_endpoint') ?? '',
    image_edit_model_name: getFieldValue('image_edit_model_name') ?? '',
    default_video_analysis_model: getFieldValue('default_video_analysis_model') ?? 'nvidia/nemotron-nano-12b-v2-vl:free',
    default_video_generation_model: getFieldValue('default_video_generation_model') ?? '',
    whisper_cpp_binary_path: getFieldValue('whisper_cpp_binary_path') ?? '',
    whisper_cpp_model_path: getFieldValue('whisper_cpp_model_path') ?? '',
    ffmpeg_binary_path: getFieldValue('ffmpeg_binary_path') ?? 'ffmpeg',
    image_edit_enabled: getFieldValue('image_edit_enabled') ?? false,
    video_enable_vision: getFieldValue('video_enable_vision') ?? false,
    video_frame_sample_seconds: getFieldValue('video_frame_sample_seconds') ?? 5,
    temperature: getFieldValue('temperature') ?? 0.7,
    system_prompt: getFieldValue('system_prompt') ?? 'Você é uma assistente útil, objetiva e confiável.',
    assistant_name: getFieldValue('assistant_name') ?? 'Kai',
    http_referer: getFieldValue('http_referer') ?? '',
    x_title: getFieldValue('x_title') ?? '',
    request_timeout_seconds: getFieldValue('request_timeout_seconds') ?? 25,
    max_video_upload_mb: getFieldValue('max_video_upload_mb') ?? 20,
    persist_multimodal_history: getFieldValue('persist_multimodal_history') ?? true,
  };

  const res = await fetch('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  document.getElementById('settings-status').textContent = res.ok ? 'Salvo com sucesso.' : 'Erro ao salvar.';
};

loadSettings();
