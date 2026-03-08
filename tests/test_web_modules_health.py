from apps.turret.state import SharedState
from apps.turret.web import build_app


class DummyServoService:
    def set_angle(self, angle: float, force: bool = False) -> float:
        return angle


def test_health_exposes_modular_status():
    cfg = {
        "web": {"stream_sleep_ms": 50},
        "servo": {"center_angle": 90},
    }
    state = SharedState(jpeg_quality=50, show_mask=True)
    state.set_vision_running(True)
    state.set_vision_fps(14.5)

    app = build_app(cfg, state, DummyServoService())
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["modules"]["vision"]["running"] is True
    assert data["modules"]["vision"]["fps"] == 14.5
    assert "servo" in data["modules"]
