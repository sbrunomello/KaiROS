import sys
import types

# Evita dependência nativa de OpenCV durante o teste unitário.
sys.modules.setdefault("cv2", types.SimpleNamespace())

from apps.bot import bot_service


class _DummyThread:
    started = False

    def __init__(self, *, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        _DummyThread.started = True


class _DummyVisionService:
    created = False

    def __init__(self, cfg, state, servo_service):
        _DummyVisionService.created = True
        self.model_classes = []
        self.recognition_modes = ["color"]
        self.color_presets = ["blue"]

    def run(self):
        return None


class _DummyApp:
    run_called = False

    def run(self, **_kwargs):
        _DummyApp.run_called = True


def test_run_service_keeps_camera_pipeline_when_detector_disabled(monkeypatch):
    cfg = bot_service.deep_merge(
        bot_service.DEFAULT_CONFIG,
        {
            "detector": {"enabled": False},
            "web": {"host": "127.0.0.1", "port": 18080},
        },
    )

    monkeypatch.setattr(bot_service, "VisionService", _DummyVisionService)
    monkeypatch.setattr(bot_service.threading, "Thread", _DummyThread)
    monkeypatch.setattr(bot_service, "build_app", lambda *_args, **_kwargs: _DummyApp())

    bot_service.run_service(cfg)

    assert _DummyVisionService.created is True
    assert _DummyThread.started is True
    assert _DummyApp.run_called is True
