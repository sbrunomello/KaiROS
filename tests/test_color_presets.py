from apps.bot.runtime.settings import RuntimeSettingsStore, VisionRuntimeSettings
from apps.bot.state import SharedState
from apps.bot.web import build_app


class DummyServoService:
    def set_angle(self, angle: float, force: bool = False) -> float:
        return angle


def test_classes_endpoint_exposes_all_option():
    cfg = {"web": {"stream_sleep_ms": 50}, "servo": {"center_angle": 90}, "detector": {}, "render": {}, "tracking": {}}
    state = SharedState(jpeg_quality=50, show_mask=True, runtime_settings=RuntimeSettingsStore(VisionRuntimeSettings()))
    app = build_app(cfg, state, DummyServoService(), classes=["person", "bottle"])
    client = app.test_client()

    response = client.get("/api/vision/classes")
    data = response.get_json()
    assert response.status_code == 200
    assert data["classes"][0] == "all"
    assert "person" in data["classes"]
