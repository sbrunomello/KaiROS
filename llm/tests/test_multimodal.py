from io import BytesIO


from llm.app.services.multimodal_service import ImageGenerationService, ModelCatalogService
from llm.app.services.openrouter_client import OpenRouterHTTPError


def test_model_catalog_filters_image_models():
    class FakeClient:
        def get_models(self):
            return [
                {"id": "text:free", "name": "Text", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
                {"id": "img:free", "name": "Image", "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
                {"id": "img-paid", "name": "Image Paid", "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
            ]

    result = ModelCatalogService(client=FakeClient()).get_capabilities()
    assert [m["id"] for m in result["image_models"]] == ["img:free", "img-paid"]
    assert [m["id"] for m in result["image_models_free"]] == ["img:free"]


def test_model_catalog_filters_video_input_models():
    class FakeClient:
        def get_models(self):
            return [
                {"id": "text", "name": "Text", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
                {"id": "video", "name": "Video", "architecture": {"input_modalities": ["text", "video"], "output_modalities": ["text"]}},
            ]

    result = ModelCatalogService(client=FakeClient()).get_capabilities()
    assert [m["id"] for m in result["video_input_models"]] == ["video"]


def test_model_catalog_does_not_classify_text_model_as_image():
    class FakeClient:
        def get_models(self):
            return [
                {"id": "some-model:free", "name": "Some", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
            ]

    result = ModelCatalogService(client=FakeClient()).get_capabilities()
    assert result["image_models"] == []
    assert result["default_image_model"] == ""


def test_image_payload_matches_openrouter_chat_completion_shape():
    payload = ImageGenerationService().build_payload(model="img:free", prompt="gato")
    assert payload["model"] == "img:free"
    assert payload["modalities"] == ["text", "image"]
    assert payload["messages"][0]["content"][0] == {"type": "text", "text": "gato"}


def test_generate_image_openrouter_error_returns_real_body(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img:free', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [],
        'image_models': [{'id': 'img:free', 'name': 'img', 'input_modalities': [], 'output_modalities': ['image'], 'is_free': True, 'supports_image_generation': True, 'supports_video_input': False}],
        'image_models_free': [{'id': 'img:free', 'name': 'img', 'input_modalities': [], 'output_modalities': ['image'], 'is_free': True, 'supports_image_generation': True, 'supports_video_input': False}],
        'image_models_paid': [], 'video_input_models': [], 'video_generation_models': [], 'default_image_model': 'img:free'
    })

    def raise_error(*args, **kwargs):
        raise OpenRouterHTTPError(status_code=404, url='https://openrouter.ai/api/v1/chat/completions', request_payload={}, response_text='{"error":"No such model"}')

    monkeypatch.setattr('llm.app.services.multimodal_service.ImageGenerationService.generate', raise_error)

    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'img:free'})
    assert res.status_code == 502
    assert 'No such model' in res.json()['detail']


def test_generate_image_uses_only_configured_default_model(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img:free', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [],
        'image_models': [{'id': 'img:free', 'name': 'img', 'input_modalities': [], 'output_modalities': ['image'], 'is_free': True, 'supports_image_generation': True, 'supports_video_input': False}],
        'image_models_free': [{'id': 'img:free', 'name': 'img', 'input_modalities': [], 'output_modalities': ['image'], 'is_free': True, 'supports_image_generation': True, 'supports_video_input': False}],
        'image_models_paid': [], 'video_input_models': [], 'video_generation_models': [], 'default_image_model': 'img:free'
    })
    called = {}

    def fake_generate(_self, settings, model, prompt):
        called['model'] = model
        return {'image_url': 'https://example.com/x.png', 'text': 'ok'}

    monkeypatch.setattr('llm.app.services.multimodal_service.ImageGenerationService.generate', fake_generate)

    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'text-only'})
    assert res.status_code == 200
    assert res.json()['model'] == 'img:free'
    assert called['model'] == 'img:free'


def test_analyze_video_uses_only_configured_default_model(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img:free', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'image_models_free': [], 'image_models_paid': [],
        'video_input_models': [{'id': 'vid-model', 'name': 'vid-model', 'input_modalities': ['video'], 'output_modalities': ['text'], 'is_free': False, 'supports_image_generation': False, 'supports_video_input': True}],
        'video_generation_models': [], 'default_image_model': 'img:free'
    })

    called = {}

    def fake_analyze(_self, settings, model, prompt, filename, content_type, raw_bytes):
        called['model'] = model
        return 'ok'

    monkeypatch.setattr('llm.app.services.multimodal_service.VideoAnalysisService.analyze', fake_analyze)

    files = {'video_file': ('test.mp4', BytesIO(b'abc'), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'desc', 'model': 'other-model'}, files=files)
    assert res.status_code == 200
    assert res.json()['model'] == 'vid-model'
    assert called['model'] == 'vid-model'


def test_chat_regression_still_works(client):
    chat = client.post('/api/chats', headers={'X-Username': 'usuario1'}, json={})
    cid = chat.json()['id']
    msg = client.post(f'/api/chat/{cid}/messages', headers={'X-Username': 'usuario1'}, json={'content': 'oi'})
    assert msg.status_code in {200, 502}


def test_video_invalid_upload_error(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img:free', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'image_models_free': [], 'image_models_paid': [],
        'video_input_models': [{'id': 'vid-model', 'name': 'vid-model', 'input_modalities': ['video'], 'output_modalities': ['text'], 'is_free': False, 'supports_image_generation': False, 'supports_video_input': True}],
        'video_generation_models': [], 'default_image_model': 'img:free'
    })

    files = {'video_file': ('test.txt', BytesIO(b'abc'), 'text/plain')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'desc', 'model': 'vid-model'}, files=files)
    assert res.status_code == 400
