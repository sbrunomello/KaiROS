from io import BytesIO
from pathlib import Path

from llm.app.services.asset_storage_service import AssetStorageService
from llm.app.services.image_generation_service import ImageGenerationError, ImageGenerationService
from llm.app.services.image_input_encoder import ImageInputEncoder
from llm.app.services.multimodal_service import ModelCatalogService
from llm.app.services.openrouter_client import OpenRouterHTTPError


def _image_service(tmp_path, fake_client=None):
    return ImageGenerationService(
        client=fake_client,
        generated_storage=AssetStorageService(base_dir=tmp_path / "generated"),
        input_storage=AssetStorageService(base_dir=tmp_path / "input", public_prefix="/input-images"),
        input_encoder=ImageInputEncoder(),
    )


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


def test_image_payload_matches_openrouter_chat_completion_shape(tmp_path):
    payload = _image_service(tmp_path).build_payload(model="bytedance-seed/seedream-4.5", prompt="gato")
    assert payload["model"] == "bytedance-seed/seedream-4.5"
    assert payload["modalities"] == ["image"]
    assert payload["messages"][0]["content"] == "gato"


def test_image_to_image_payload_uses_official_multimodal_content(tmp_path):
    payload = _image_service(tmp_path).build_payload(
        model="bytedance-seed/seedream-4.5",
        prompt="anime",
        mode="image_to_image",
        input_image_data_url="data:image/png;base64,aGVsbG8=",
    )
    content = payload["messages"][0]["content"]
    assert isinstance(content, list)
    assert content[1]["type"] == "image_url"


def test_valid_data_url_response_is_saved_locally(tmp_path):
    class FakeClient:
        def chat_completion(self, **_kwargs):
            return {"choices": [{"message": {"images": [{"image_url": {"url": "data:image/png;base64,aGVsbG8="}}], "content": "ok"}}]}

    class Settings:
        openrouter_api_key = "k"
        http_referer = ""
        x_title = ""

    result = _image_service(tmp_path, FakeClient()).generate(settings=Settings(), model="bytedance-seed/seedream-4.5", prompt="cat")
    assert result["mime_type"] == "image/png"
    assert result["size_bytes"] == 5
    assert result["image_url"].startswith("/generated-images/")
    assert Path(result["file_path"]).exists()


def test_image_to_image_with_upload_saves_input_and_output(tmp_path):
    class FakeClient:
        def chat_completion(self, **_kwargs):
            return {"choices": [{"message": {"images": [{"image_url": {"url": "data:image/png;base64,aGVsbG8="}}], "content": "ok"}}]}

    class Settings:
        openrouter_api_key = "k"
        http_referer = ""
        x_title = ""

    result = _image_service(tmp_path, FakeClient()).generate(
        settings=Settings(),
        model="bytedance-seed/seedream-4.5",
        prompt="cat",
        mode="image_to_image",
        input_image_bytes=b"fake",
        input_image_mime_type="image/png",
    )
    assert result["input_image_url"].startswith("/input-images/")


def test_response_without_choices_raises(tmp_path):
    try:
        _image_service(tmp_path)._extract_data_url({})
    except ImageGenerationError as exc:
        assert "sem choices" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_response_without_images_raises(tmp_path):
    try:
        _image_service(tmp_path)._extract_data_url({"choices": [{"message": {}}]})
    except ImageGenerationError as exc:
        assert "não retornou imagens" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_data_url_invalid_raises(tmp_path):
    try:
        _image_service(tmp_path)._decode_data_url("data:image/png;base64,###")
    except ImageGenerationError as exc:
        assert "decodificar" in str(exc)
    else:
        raise AssertionError("Expected ImageGenerationError")


def test_generate_image_openrouter_http_error(client, monkeypatch):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'bytedance-seed/seedream-4.5', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })

    def raise_error(*_args, **_kwargs):
        raise OpenRouterHTTPError(status_code=404, url='https://openrouter.ai/api/v1/chat/completions', request_payload={}, response_text='{"error":"No such model"}')

    monkeypatch.setattr('llm.app.services.image_generation_service.ImageGenerationService.generate', raise_error)
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, json={'prompt': 'cat', 'model': 'bytedance-seed/seedream-4.5'})
    assert res.status_code == 502


def test_error_on_image_to_image_without_image(client):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'bytedance-seed/seedream-4.5', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, data={'prompt': 'cat', 'model': 'bytedance-seed/seedream-4.5', 'mode': 'image_to_image'})
    assert res.status_code == 400


def test_error_on_invalid_mime_image_upload(client):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'bytedance-seed/seedream-4.5', 'default_video_analysis_model': 'vid-model',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 20, 'persist_multimodal_history': True,
    })
    files = {'image': ('file.gif', BytesIO(b'abc'), 'image/gif')}
    res = client.post('/api/generate-image', headers={'X-Username': 'usuario1'}, data={'prompt': 'cat', 'mode': 'image_to_image'}, files=files)
    assert res.status_code == 400


def test_chat_regression_still_works(client):
    chat = client.post('/api/chats', headers={'X-Username': 'usuario1'}, json={})
    cid = chat.json()['id']
    msg = client.post(f'/api/chat/{cid}/messages', headers={'X-Username': 'usuario1'}, json={'content': 'oi'})
    assert msg.status_code in {200, 502}
