def test_settings_read_write(client):
    original = client.get('/api/settings').json()
    assert original['model_name']

    payload = {
        'openrouter_api_key': 'abc123',
        'groq_api_key': 'groq-abc',
        'huggingface_api_key': 'hf-abc',
        'cloudflare_api_token': 'cf-token',
        'cloudflare_account_id': 'cf-account',
        'together_api_key': 'tog-abc',
        'deepinfra_api_key': 'deep-abc',
        'chat_provider': 'openrouter',
        'chat_fallback_provider': 'groq',
        'speech_provider': 'local',
        'vision_provider': 'openrouter',
        'vision_fallback_provider': 'deepinfra',
        'image_gen_provider': 'hf',
        'image_gen_fallback_provider': 'openrouter',
        'image_edit_provider': 'hf',
        'image_edit_fallback_provider': 'openrouter',
        'video_analysis_mode': 'pipeline',
        'model_name': 'deepseek/deepseek-chat',
        'chat_model_name': 'llama-3.3-70b-versatile',
        'speech_model_name': 'whisper-local',
        'vision_model_name': 'meta-llama/llama-3.2-11b-vision-instruct',
        'default_image_model': 'black-forest-labs/FLUX.1-schnell',
        'openrouter_default_image_model': 'bytedance-seed/seedream-4.5',
        'hf_default_image_model': 'black-forest-labs/FLUX.1-schnell',
        'cloudflare_default_chat_model': '@cf/meta/llama-3.1-8b-instruct',
        'cloudflare_default_vision_model': '@cf/llava-hf/llava-1.5-7b-hf',
        'cloudflare_default_image_model': '@cf/stabilityai/stable-diffusion-xl-base-1.0',
        'together_default_chat_model': 'meta-llama/Llama-3.1-8B-Instruct-Turbo',
        'together_default_vision_model': 'meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo',
        'together_default_image_model': 'black-forest-labs/FLUX.1-schnell',
        'deepinfra_default_chat_model': 'meta-llama/Meta-Llama-3.1-8B-Instruct',
        'deepinfra_default_vision_model': 'meta-llama/Llama-3.2-11B-Vision-Instruct',
        'deepinfra_default_image_model': 'black-forest-labs/FLUX.1-schnell',
        'image_edit_model_name': 'black-forest-labs/FLUX.1-Kontext-dev',
        'default_video_analysis_model': 'google/gemini-2.5-flash',
        'default_video_generation_model': 'meta/video-gen',
        'whisper_cpp_binary_path': '/usr/local/bin/whisper-cli',
        'whisper_cpp_model_path': '/models/ggml-base.bin',
        'ffmpeg_binary_path': '/usr/bin/ffmpeg',
        'image_edit_enabled': True,
        'video_enable_vision': True,
        'video_frame_sample_seconds': 7,
        'temperature': 0.3,
        'system_prompt': 'Seja objetivo.',
        'assistant_name': 'Nora',
        'http_referer': 'http://localhost',
        'x_title': 'KaiROS LLM',
        'request_timeout_seconds': 45,
        'max_video_upload_mb': 42,
        'persist_multimodal_history': False,
    }
    res = client.put('/api/settings', json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body['model_name'] == 'deepseek/deepseek-chat'
    assert body['chat_provider'] == 'openrouter'
    assert body['image_edit_enabled'] is True

    reloaded = client.get('/api/settings').json()
    assert reloaded['assistant_name'] == 'Nora'
    assert reloaded['video_analysis_mode'] == 'pipeline'
    assert reloaded['ffmpeg_binary_path'] == '/usr/bin/ffmpeg'


def test_settings_page_contains_new_multi_provider_fields(client):
    response = client.get('/settings')

    assert response.status_code == 200
    html = response.text
    assert 'id="chat_provider"' in html
    assert 'id="chat_fallback_provider"' in html
    assert 'id="speech_provider"' in html
    assert 'id="vision_provider"' in html
    assert 'id="image_gen_provider"' in html
    assert 'id="image_edit_provider"' in html
    assert 'id="video_analysis_mode"' in html
    assert 'id="groq_api_key"' in html
    assert 'id="huggingface_api_key"' in html
    assert 'id="cloudflare_api_token"' in html
    assert 'id="cloudflare_account_id"' in html
    assert 'id="together_api_key"' in html
    assert 'id="deepinfra_api_key"' in html
    assert 'id="vision_fallback_provider"' in html
    assert 'id="image_gen_fallback_provider"' in html
    assert 'id="image_edit_fallback_provider"' in html
    assert 'id="image_edit_enabled"' in html
    assert 'id="video_enable_vision"' in html
