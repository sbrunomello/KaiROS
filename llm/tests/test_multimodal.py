from io import BytesIO

from llm.app.services.multimodal_service import ModelCatalogService


def test_model_catalog_filters_by_capability(monkeypatch):
    class FakeClient:
        def get_models(self):
            return [
                {"id": "a", "name": "A", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
                {"id": "img", "name": "Img", "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
                {"id": "vid", "name": "Vid", "architecture": {"input_modalities": ["video"], "output_modalities": ["text"]}},
            ]

    result = ModelCatalogService(client=FakeClient()).get_capabilities()
    assert [m["id"] for m in result["image_models"]] == ["img"]
    assert [m["id"] for m in result["video_input_models"]] == ["vid"]


def test_generate_image_success(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img-model', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [{'id': 'img-model', 'name': 'img-model', 'input_modalities': [], 'output_modalities': ['image']}],
        'video_input_models': [], 'video_generation_models': []
    })
    monkeypatch.setattr('llm.app.services.multimodal_service.ImageGenerationService.generate', lambda _self, settings, model, prompt: {'image_url': 'http://x/img.png', 'text': 'ok'})

    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'img-model'})
    assert res.status_code == 200
    assert res.json()['image_url']


def test_missing_api_key_error(client, monkeypatch):
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [{'id': 'img-model', 'name': 'img-model', 'input_modalities': [], 'output_modalities': ['image']}],
        'video_input_models': [], 'video_generation_models': []
    })
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'img-model'})
    assert res.status_code == 400


def test_incompatible_model_error(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img-model', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'video_input_models': [], 'video_generation_models': []
    })
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'img-model'})
    assert res.status_code == 400


def test_video_invalid_upload_error(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img-model', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'video_input_models': [{'id': 'vid-model', 'name': 'vid-model', 'input_modalities': ['video'], 'output_modalities': ['text']}], 'video_generation_models': []
    })

    files = {'video_file': ('test.txt', BytesIO(b'abc'), 'text/plain')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'desc', 'model': 'vid-model'}, files=files)
    assert res.status_code == 400


def test_video_analysis_and_history(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'img-model', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'video_input_models': [{'id': 'vid-model', 'name': 'vid-model', 'input_modalities': ['video'], 'output_modalities': ['text']}], 'video_generation_models': []
    })
    monkeypatch.setattr('llm.app.services.multimodal_service.VideoAnalysisService.analyze', lambda _self, settings, model, prompt, filename, content_type, raw_bytes: 'resultado mock')

    files = {'video_file': ('test.mp4', BytesIO(b'abc'), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'desc', 'model': 'vid-model'}, files=files)
    assert res.status_code == 200
    history = client.get('/api/history/multimodal', headers={'X-Username': 'usuario1'})
    assert history.status_code == 200
    assert history.json()[0]['item_type'] == 'video_analysis'
