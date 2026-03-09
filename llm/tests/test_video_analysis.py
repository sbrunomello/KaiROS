from io import BytesIO

from llm.app.services.video_analysis_service import VideoAnalysisService
from llm.app.services.video_input_encoder import VideoInputEncoder, VideoInputEncoderError


class SettingsStub:
    openrouter_api_key = "k"
    http_referer = ""
    x_title = ""


def _put_settings(client):
    client.put('/api/settings', json={
        'openrouter_api_key': 'k', 'model_name': 'openrouter/auto', 'temperature': 0.7,
        'system_prompt': 'x', 'assistant_name': 'Kai', 'http_referer': '', 'x_title': '',
        'default_image_model': 'bytedance-seed/seedream-4.5', 'default_video_analysis_model': 'nvidia/nemotron-nano-12b-v2-vl:free',
        'default_video_generation_model': '', 'request_timeout_seconds': 25,
        'max_video_upload_mb': 1, 'persist_multimodal_history': True,
    })


def test_video_input_encoder_rejects_invalid_mime():
    enc = VideoInputEncoder()
    try:
        enc.validate_mime_type('application/octet-stream')
    except VideoInputEncoderError as exc:
        assert 'não suportado' in str(exc)
    else:
        raise AssertionError('expected VideoInputEncoderError')


def test_video_payload_matches_openrouter_multimodal_shape():
    payload = VideoAnalysisService().build_payload(
        model='nvidia/nemotron-nano-12b-v2-vl:free',
        prompt='Descreva',
        video_data_url='data:video/mp4;base64,ZmFrZQ==',
        reasoning_enabled=True,
    )
    assert payload['messages'][0]['content'][1]['type'] == 'video_url'
    assert payload['reasoning'] == {'enabled': True}


def test_video_analysis_success(client, monkeypatch):
    _put_settings(client)

    class FakeClient:
        def chat_completion(self, **_kwargs):
            return {'choices': [{'message': {'content': 'Resumo do vídeo'}}], 'reasoning_details': {'trace': 'ok'}}

    monkeypatch.setattr('llm.app.routes.api_multimodal.VideoAnalysisService', lambda **_kwargs: VideoAnalysisService(client=FakeClient()))
    files = {'video_file': ('video.mp4', BytesIO(b'fake-video'), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'Resuma', 'model': 'nvidia/nemotron-nano-12b-v2-vl:free', 'reasoning_enabled': 'true'}, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data['result'] == 'Resumo do vídeo'
    assert data['reasoning_enabled'] is True


def test_video_analysis_error_without_file(client):
    _put_settings(client)
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'Resuma', 'model': 'nvidia/nemotron-nano-12b-v2-vl:free'})
    assert res.status_code == 400


def test_video_analysis_invalid_mime(client):
    _put_settings(client)
    files = {'video_file': ('video.bin', BytesIO(b'abc'), 'application/octet-stream')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'Resuma', 'model': 'nvidia/nemotron-nano-12b-v2-vl:free'}, files=files)
    assert res.status_code == 400


def test_video_analysis_limit_exceeded(client):
    _put_settings(client)
    files = {'video_file': ('video.mp4', BytesIO(b'x' * (2 * 1024 * 1024)), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'Resuma', 'model': 'nvidia/nemotron-nano-12b-v2-vl:free'}, files=files)
    assert res.status_code == 400


def test_video_analysis_response_without_choices_returns_502(client, monkeypatch):
    _put_settings(client)

    class FakeClient:
        def chat_completion(self, **_kwargs):
            return {}

    monkeypatch.setattr('llm.app.routes.api_multimodal.VideoAnalysisService', lambda **_kwargs: VideoAnalysisService(client=FakeClient()))
    files = {'video_file': ('video.mp4', BytesIO(b'fake-video'), 'video/mp4')}
    res = client.post('/api/analyze-video', headers={'X-Username': 'usuario1'}, data={'prompt': 'Resuma', 'model': 'nvidia/nemotron-nano-12b-v2-vl:free'}, files=files)
    assert res.status_code == 502


def test_video_analysis_reasoning_disabled_omits_reasoning_block():
    payload = VideoAnalysisService().build_payload(
        model='nvidia/nemotron-nano-12b-v2-vl:free',
        prompt='Descreva',
        video_data_url='data:video/mp4;base64,ZmFrZQ==',
        reasoning_enabled=False,
    )
    assert 'reasoning' not in payload


def test_image_regression_generate_video_endpoint_still_placeholder(client):
    res = client.post('/api/generate-video')
    assert res.status_code == 501
