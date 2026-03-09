from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from llm.app.services.speech_service import SpeechService
from llm.app.services.video_analysis_service import VideoAnalysisService, VideoAnalysisResult


def _base_settings_payload(**overrides):
    payload = {
        "openrouter_api_key": "or-key",
        "groq_api_key": "g-key",
        "huggingface_api_key": "hf-key",
        "model_name": "openrouter/auto",
        "chat_model_name": "openrouter/auto",
        "default_image_model": "legacy-image",
        "openrouter_default_image_model": "bytedance-seed/seedream-4.5",
        "hf_default_image_model": "black-forest-labs/FLUX.1-schnell",
        "default_video_analysis_model": "nvidia/nemotron-nano-12b-v2-vl:free",
        "default_video_generation_model": "",
        "temperature": 0.7,
        "system_prompt": "x",
        "assistant_name": "Kai",
        "http_referer": "",
        "x_title": "",
        "request_timeout_seconds": 25,
        "max_video_upload_mb": 20,
        "persist_multimodal_history": True,
        "image_gen_provider": "hf",
        "image_edit_provider": "hf",
        "image_edit_enabled": False,
    }
    payload.update(overrides)
    return payload


def test_generate_image_hf_path_skips_openrouter_catalog(client, monkeypatch):
    client.put("/api/settings", json=_base_settings_payload(image_gen_provider="hf", openrouter_api_key=""))

    monkeypatch.setattr(
        "llm.app.routes.api_multimodal.ModelCatalogService.get_capabilities",
        lambda self: (_ for _ in ()).throw(AssertionError("should not call openrouter catalog for hf")),
    )

    def fake_generate(self, **kwargs):
        assert kwargs["model"] == "black-forest-labs/FLUX.1-schnell"
        return {
            "image_url": "/generated-images/out.png",
            "file_path": "/tmp/out.png",
            "mime_type": "image/png",
            "size_bytes": 123,
            "text": "ok",
            "input_image_url": "",
        }

    monkeypatch.setattr("llm.app.services.image_generation_service.ImageGenerationService.generate", fake_generate)
    res = client.post("/api/generate-image", headers={"X-Username": "user1"}, json={"prompt": "cat"})
    assert res.status_code == 200
    assert res.json()["model"] == "black-forest-labs/FLUX.1-schnell"


def test_image_to_image_feature_flag_off(client):
    client.put("/api/settings", json=_base_settings_payload(image_edit_enabled=False))
    files = {"image": ("file.png", BytesIO(b"fake-png"), "image/png")}
    res = client.post(
        "/api/generate-image",
        headers={"X-Username": "user1"},
        data={"prompt": "cat", "mode": "image_to_image", "model": "hf-model"},
        files=files,
    )
    assert res.status_code == 400
    assert "desabilitado" in res.json()["detail"]


def test_image_to_image_feature_flag_on(client, monkeypatch):
    client.put("/api/settings", json=_base_settings_payload(image_edit_enabled=True))

    class EditResult:
        mime_type = "image/png"
        image_bytes = b"abc"
        text = "done"

    monkeypatch.setattr(
        "llm.app.providers.registry.ProviderRegistry.resolve_image_edit",
        lambda self, settings: SimpleNamespace(edit=lambda image_path, prompt, options: EditResult()),
    )

    files = {"image": ("file.png", BytesIO(b"fake-png"), "image/png")}
    res = client.post(
        "/api/generate-image",
        headers={"X-Username": "user1"},
        data={"prompt": "cat", "mode": "image_to_image", "model": "hf-model"},
        files=files,
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "image_to_image"


def test_speech_service_fallback_to_local(monkeypatch):
    class GroqFail:
        def transcribe(self, audio_path, options):
            raise ValueError("groq down")

    class LocalOk:
        def transcribe(self, audio_path, options):
            from llm.app.providers.base import SpeechResult

            return SpeechResult(text="fallback text", model_used="local-whisper.cpp")

    registry = SimpleNamespace(
        resolve_speech=lambda settings: GroqFail(),
        speech_providers={"local": LocalOk()},
    )
    service = SpeechService(registry=registry)
    settings = SimpleNamespace(speech_provider="groq")

    result = service.transcribe("/tmp/fake.wav", settings)
    assert result["provider"] == "local"
    assert result["text"] == "fallback text"


def test_video_pipeline_basic(monkeypatch):
    service = VideoAnalysisService()

    monkeypatch.setattr(service.audio_extractor, "extract", lambda video_path, ffmpeg_binary_path: "/tmp/audio.wav")
    monkeypatch.setattr(service.frame_sampler, "sample", lambda video_path, interval_seconds, ffmpeg_binary_path='ffmpeg': [])

    from llm.app.providers.base import SpeechResult

    registry = SimpleNamespace(
        resolve_speech=lambda settings: SimpleNamespace(transcribe=lambda audio_path, options: SpeechResult(text="transcript", model_used="groq-whisper")),
        resolve_chat=lambda settings: SimpleNamespace(generate=lambda messages, options: SimpleNamespace(content="final", model_used="groq-chat")),
        speech_providers={"local": SimpleNamespace(transcribe=lambda audio_path, options: SpeechResult(text="local", model_used="local-whisper.cpp"))},
    )
    service.registry = registry

    settings = SimpleNamespace(
        video_analysis_mode="pipeline",
        ffmpeg_binary_path="ffmpeg",
        video_enable_vision=False,
        video_frame_sample_seconds=5,
        speech_provider="groq",
    )

    result = service.analyze(
        settings=settings,
        model="unused",
        prompt="resuma",
        filename="video.mp4",
        content_type="video/mp4",
        raw_bytes=b"video",
        reasoning_enabled=False,
    )
    assert isinstance(result, VideoAnalysisResult)
    assert result.text == "final"


def test_analyze_image_requires_openrouter_key_when_provider_openrouter(client):
    client.put(
        "/api/settings",
        json=_base_settings_payload(vision_provider="openrouter", openrouter_api_key="", groq_api_key=""),
    )
    files = {"image_file": ("x.png", BytesIO(b"\x89PNG\r\n\x1a\n1234"), "image/png")}
    res = client.post("/api/analyze-image", data={"prompt": "desc"}, files=files, headers={"X-Username": "user1"})
    assert res.status_code == 400
    assert "OpenRouter API key" in res.json()["detail"]


def test_frame_sampling_uses_ffmpeg_binary_path(monkeypatch, tmp_path):
    from llm.app.services.video_analysis_service import FrameSamplingService

    captured = {}

    def fake_run(cmd, capture_output, text):
        captured["cmd"] = cmd

        class R:
            returncode = 0
            stderr = ""
            stdout = ""

        # create one frame so service returns something predictable
        out_dir = tmp_path / "video.mp4_frames"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "frame_001.jpg").write_bytes(b"x")
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    video_path = str(tmp_path / "video.mp4")
    Path(video_path).write_bytes(b"video")

    frames = FrameSamplingService().sample(video_path, 2, ffmpeg_binary_path="/usr/local/bin/ffmpeg")
    assert captured["cmd"][0] == "/usr/local/bin/ffmpeg"
    assert len(frames) == 1


def test_video_pipeline_uses_speech_service_fallback(monkeypatch):
    service = VideoAnalysisService()
    monkeypatch.setattr(service.audio_extractor, "extract", lambda video_path, ffmpeg_binary_path: "/tmp/audio.wav")

    captured = {}

    def fake_transcribe(self, audio_path, settings):
        return {"text": "fallback transcript", "model": "local-whisper.cpp", "provider": "local"}

    def fake_chat_generate(messages, options):
        captured["messages"] = messages
        return SimpleNamespace(content="ok", model_used="groq-chat")

    registry = SimpleNamespace(
        resolve_chat=lambda settings: SimpleNamespace(generate=fake_chat_generate),
    )
    service.registry = registry

    monkeypatch.setattr("llm.app.services.video_analysis_service.SpeechService.transcribe", fake_transcribe)

    settings = SimpleNamespace(
        video_analysis_mode="pipeline",
        ffmpeg_binary_path="ffmpeg",
        video_enable_vision=False,
        video_frame_sample_seconds=5,
        speech_provider="groq",
    )

    result = service.analyze(
        settings=settings,
        model="unused",
        prompt="resuma",
        filename="video.mp4",
        content_type="video/mp4",
        raw_bytes=b"video",
        reasoning_enabled=False,
    )

    assert result.text == "ok"
    assert "fallback transcript" in captured["messages"][0]["content"]
