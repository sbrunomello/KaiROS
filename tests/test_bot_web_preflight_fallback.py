import sys
import types

import pytest

from apps.bot import bot_web
from apps.bot.runtime.preflight import PreflightError, PreflightFailure


class _Args(types.SimpleNamespace):
    no_servo = False
    host = None
    port = None
    width = None
    height = None
    fps = None
    no_detector = False
    config = "apps/bot/config.yaml"


def test_main_falls_back_to_detector_disabled_when_preflight_fails_for_detector(monkeypatch, capsys):
    cfg = {"detector": {"enabled": True}}
    called = {}

    monkeypatch.setattr(bot_web, "parse_args", lambda: _Args())

    def fake_preflight(*, detector_enabled: bool):
        assert detector_enabled is True
        raise PreflightError(
            "torch SIGILL",
            failure=PreflightFailure(
                module_name="torch",
                rationale="inferência YOLO",
                detector_related=True,
                signal_name="SIGILL",
            ),
        )

    monkeypatch.setattr(bot_web, "run_binary_dependency_preflight", fake_preflight)

    fake_bot_service = types.SimpleNamespace(
        load_config=lambda _path: cfg,
        apply_overrides=lambda _cfg, _args: None,
        run_service=lambda input_cfg: called.setdefault("detector_enabled", input_cfg["detector"]["enabled"]),
    )
    monkeypatch.setitem(sys.modules, "apps.bot.bot_service", fake_bot_service)

    bot_web.main()

    assert called["detector_enabled"] is False
    out = capsys.readouterr().out
    assert "Detector desabilitado automaticamente" in out


def test_main_keeps_failing_for_non_detector_preflight_error(monkeypatch):
    cfg = {"detector": {"enabled": True}}

    monkeypatch.setattr(bot_web, "parse_args", lambda: _Args())

    def fake_preflight(*, detector_enabled: bool):
        assert detector_enabled is True
        raise PreflightError(
            "cv2 import failed",
            failure=PreflightFailure(
                module_name="cv2",
                rationale="captura/render de vídeo",
                detector_related=False,
            ),
        )

    monkeypatch.setattr(bot_web, "run_binary_dependency_preflight", fake_preflight)

    fake_bot_service = types.SimpleNamespace(
        load_config=lambda _path: cfg,
        apply_overrides=lambda _cfg, _args: None,
        run_service=lambda _cfg: pytest.fail("não deveria iniciar"),
    )
    monkeypatch.setitem(sys.modules, "apps.bot.bot_service", fake_bot_service)

    with pytest.raises(SystemExit) as exc_info:
        bot_web.main()

    assert "[KAIROS PRECHECK] cv2 import failed" in str(exc_info.value)
