from apps.turret.turret_service import DEFAULT_CONFIG, deep_merge, load_config


def test_deep_merge_keeps_defaults():
    merged = deep_merge(DEFAULT_CONFIG, {"tracking": {"color": "blue"}})
    assert merged["tracking"]["color"] == "blue"
    assert merged["camera"]["fps"] == DEFAULT_CONFIG["camera"]["fps"]


def test_load_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("tracking:\n  color: red\n", encoding="utf-8")
    cfg = load_config(str(cfg_file))
    assert cfg["tracking"]["color"] == "red"
    assert cfg["servo"]["enabled"] is True
