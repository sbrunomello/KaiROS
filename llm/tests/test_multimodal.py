from io import BytesIO
from pathlib import Path

from llm.app.services.asset_storage_service import AssetStorageService
from llm.app.services.image_generation_service import ImageGenerationError, ImageGenerationService
from llm.app.services.multimodal_service import ModelCatalogService
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


def test_model_catalog_does_not_classify_text_model_as_image():
    class FakeClient:
        def get_models(self):
            return [{"id": "text-only", "name": "Some", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}}]

    result = ModelCatalogService(client=FakeClient()).get_capabilities()
    assert result["image_models"] == []


def test_image_payload_matches_openrouter_chat_completion_shape(tmp_path):
    service = ImageGenerationService(storage=AssetStorageService(base_dir=tmp_path))
    payload = service.build_payload(model="sourceful/riverflow-v2-fast", prompt="gato")
    assert payload["model"] == "sourceful/riverflow-v2-fast"
    assert payload["modalities"] == ["image"]
    assert payload["messages"][0]["content"] == "gato"


def test_valid_data_url_response_is_saved_locally(tmp_path):
    class FakeClient:
        def chat_completion(self, **_kwargs):
            return {
                "choices": [
                    {"message": {"images": [{"image_url": {"url": "data:image/png;base64,aGVsbG8="}}], "content": "ok"}}
                ]
            }

    class Settings:
        openrouter_api_key = "k"
        http_referer = ""
        x_title = ""

    service = ImageGenerationService(client=FakeClient(), storage=AssetStorageService(base_dir=tmp_path))
    result = service.generate(settings=Settings(), model="sourceful/riverflow-v2-fast", prompt="cat")
    assert result["mime_type"] == "image/png"
    assert result["size_bytes"] == 5
    assert result["image_url"].startswith("/generated-images/")
    assert Path(result["file_path"]).exists()


def test_response_without_choices_raises(tmp_path):
    service = ImageGenerationService(storage=AssetStorageService(base_dir=tmp_path))
    try:
        service._extract_data_url({})
    except ImageGenerationError as exc:
        assert "sem choices" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_response_without_images_raises(tmp_path):
    service = ImageGenerationService(storage=AssetStorageService(base_dir=tmp_path))
    try:
        service._extract_data_url({"choices": [{"message": {}}]})
    except ImageGenerationError as exc:
        assert "não retornou imagens" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_invalid_image_url_raises(tmp_path):
    service = ImageGenerationService(storage=AssetStorageService(base_dir=tmp_path))
    try:
        service._extract_data_url({"choices": [{"message": {"images": [{"image_url": {"url": "https://x"}}]}}]})
    except ImageGenerationError as exc:
        assert "data URL" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_generate_image_openrouter_http_error(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'sourceful/riverflow-v2-fast', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    def raise_error(*_args, **_kwargs):
        raise OpenRouterHTTPError(status_code=404, url='https://openrouter.ai/api/v1/chat/completions', request_payload={}, response_text='{"error":"No such model"}')

    monkeypatch.setattr('llm.app.services.image_generation_service.ImageGenerationService.generate', raise_error)

    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'sourceful/riverflow-v2-fast'})
    assert res.status_code == 502
    assert 'HTTP 404' in res.json()['detail']


def test_generate_image_uses_requested_model(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'sourceful/riverflow-v2-fast', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [],
        'image_models': [{'id': 'sourceful/riverflow-v2-fast'}, {'id': 'img-paid'}],
        'image_models_free': [], 'image_models_paid': [], 'video_input_models': [], 'video_generation_models': [],
        'default_image_model': 'sourceful/riverflow-v2-fast'
    })

    called = {}

    def fake_generate(_self, settings, model, prompt):
        called['model'] = model
        return {'image_url': '/generated-images/x.png', 'file_path': '/tmp/x.png', 'mime_type': 'image/png', 'size_bytes': 10, 'text': 'ok'}

    monkeypatch.setattr('llm.app.services.image_generation_service.ImageGenerationService.generate', fake_generate)
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'img-paid'})
    assert res.status_code == 200
    assert called['model'] == 'img-paid'


def test_analyze_video_uses_only_configured_default_model(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'sourceful/riverflow-v2-fast', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    monkeypatch.setattr('llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities', lambda _self: {
        'models': [], 'image_models': [], 'image_models_free': [], 'image_models_paid': [],
        'video_input_models': [{'id': 'vid-model', 'name': 'vid-model', 'input_modalities': ['video'], 'output_modalities': ['text'], 'is_free': False, 'supports_image_generation': False, 'supports_video_input': True}],
        'video_generation_models': [], 'default_image_model': 'sourceful/riverflow-v2-fast'
    })

    called = {}

    def fake_analyze(_self, settings, model, prompt, filename, content_type, raw_bytes):
        called['model'] = model
        return 'ok'

    monkeypatch.setattr('llm.app.services.multimodal_service.VideoAnalysisService.analyze', fake_analyze)

    files = {'video_file': ('test.mp4', BytesIO(b'abc'), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'desc', 'model': 'other-model'}, files=files)
    assert res.status_code == 200
    assert called['model'] == 'vid-model'


def test_chat_regression_still_works(client):
    chat = client.post('/api/chats', headers={'X-Username': 'usuario1'}, json={})
    cid = chat.json()['id']
    msg = client.post(f'/api/chat/{cid}/messages', headers={'X-Username': 'usuario1'}, json={'content': 'oi'})
    assert msg.status_code in {200, 502}
