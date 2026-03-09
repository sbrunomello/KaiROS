from types import SimpleNamespace

from apps.bot.bot_service import DEFAULT_CONFIG, apply_overrides, deep_merge, load_config


def test_deep_merge_keeps_defaults():
    merged = deep_merge(DEFAULT_CONFIG, {"detector": {"conf_threshold": 0.4}})
    assert merged["detector"]["conf_threshold"] == 0.4
    assert merged["camera"]["fps"] == DEFAULT_CONFIG["camera"]["fps"]


def test_load_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("detector:\n  target_class_default: person\n", encoding="utf-8")
    cfg = load_config(str(cfg_file))
    assert cfg["detector"]["target_class_default"] == "person"
    assert cfg["servo"]["enabled"] is True


def test_apply_overrides_can_disable_detector():
    cfg = deep_merge(DEFAULT_CONFIG, {})
    args = SimpleNamespace(no_servo=False, host=None, port=None, width=None, height=None, fps=None, no_detector=True)

    apply_overrides(cfg, args)

    assert cfg["detector"]["enabled"] is False
