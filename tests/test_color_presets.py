from apps.turret.tracking import COLOR_PRESETS


def test_color_presets_exist():
    for name in ["blue", "green", "red", "yellow"]:
        assert name in COLOR_PRESETS


def test_hsv_ranges_valid():
    for ranges in COLOR_PRESETS.values():
        for lower, upper in ranges:
            assert len(lower) == 3 and len(upper) == 3
            for idx in range(3):
                assert 0 <= lower[idx] <= upper[idx]
