from apps.bot.runtime.settings import RuntimeSettingsStore, VisionRuntimeSettings
from apps.bot.state import SharedState
from apps.bot.web import build_app


class DummyServoService:
    def set_angle(self, angle: float, force: bool = False) -> float:
        return angle


def test_health_exposes_modular_status():
    cfg = {"web": {"stream_sleep_ms": 50}, "servo": {"center_angle": 90}, "detector": {}, "render": {}, "tracking": {}}
    state = SharedState(jpeg_quality=50, show_mask=True, runtime_settings=RuntimeSettingsStore(VisionRuntimeSettings()))
    state.set_vision_running(True)
    state.set_vision_fps(14.5)

    app = build_app(cfg, state, DummyServoService(), classes=["person", "car"])
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["modules"]["vision"]["running"] is True
    assert data["modules"]["vision"]["fps"] == 14.5


def test_runtime_endpoint_updates_infer_n():
    cfg = {"web": {"stream_sleep_ms": 50}, "servo": {"center_angle": 90}, "detector": {}, "render": {}, "tracking": {}}
    state = SharedState(jpeg_quality=50, show_mask=True, runtime_settings=RuntimeSettingsStore(VisionRuntimeSettings()))
    app = build_app(cfg, state, DummyServoService(), classes=["person"])
    client = app.test_client()

    response = client.post("/api/vision/runtime", json={"infer_every_n_frames": 4})
    assert response.status_code == 200
    assert response.get_json()["infer_every_n_frames"] == 4
