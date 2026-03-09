import types

from apps.bot.runtime import preflight


def _ok_result():
    return types.SimpleNamespace(returncode=0, stderr="", stdout="")


def test_preflight_skips_detector_modules_when_disabled(monkeypatch):
    imported = []

    def fake_run_import_check(module_name: str):
        imported.append(module_name)
        return _ok_result()

    monkeypatch.setattr(preflight, "_run_import_check", fake_run_import_check)

    preflight.run_binary_dependency_preflight(detector_enabled=False)

    assert imported == ["cv2", "numpy"]


def test_preflight_checks_detector_modules_when_enabled(monkeypatch):
    imported = []

    def fake_run_import_check(module_name: str):
        imported.append(module_name)
        return _ok_result()

    monkeypatch.setattr(preflight, "_run_import_check", fake_run_import_check)

    preflight.run_binary_dependency_preflight(detector_enabled=True)

    assert imported == ["cv2", "numpy", "torch", "ultralytics"]
