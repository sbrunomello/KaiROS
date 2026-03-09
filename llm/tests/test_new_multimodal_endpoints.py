from io import BytesIO


def test_analyze_image_endpoint(client, monkeypatch):
    client.put(
        "/api/settings",
        json={
            "openrouter_api_key": "",
            "groq_api_key": "g",
            "huggingface_api_key": "",
            "model_name": "openrouter/auto",
            "chat_model_name": "llama-3.1-8b-instant",
            "default_image_model": "m",
            "default_video_analysis_model": "m",
            "default_video_generation_model": "",
            "temperature": 0.7,
            "system_prompt": "s",
            "assistant_name": "Kai",
            "http_referer": "",
            "x_title": "",
            "request_timeout_seconds": 25,
            "max_video_upload_mb": 20,
            "persist_multimodal_history": True,
        },
    )

    class _Vision:
        model_used = "vision-model"
        text = "descrição"

    class _Provider:
        def describe(self, image_path, prompt, options):
            return _Vision()

    monkeypatch.setattr("llm.app.routes.api_multimodal.ProviderRegistry.resolve_vision", lambda self, settings: _Provider())

    files = {"image_file": ("x.png", BytesIO(b"\x89PNG\r\n\x1a\n1234"), "image/png")}
    data = {"prompt": "Descreva"}
    response = client.post("/api/analyze-image", data=data, files=files, headers={"X-Username": "user1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["result"] == "descrição"


def test_transcribe_audio_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "llm.app.services.speech_service.SpeechService.transcribe",
        lambda self, audio_path, settings: {"text": "oi", "model": "whisper", "provider": "groq"},
    )
    files = {"audio_file": ("x.wav", BytesIO(b"RIFF....WAVE"), "audio/wav")}
    response = client.post("/api/transcribe-audio", files=files, headers={"X-Username": "user1"})
    assert response.status_code == 200
    assert response.json()["text"] == "oi"
