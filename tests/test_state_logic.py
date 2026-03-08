from apps.turret.tracking import compute_target_angle
from apps.turret.utils import clamp


def test_clamp_angle():
    assert clamp(200, 60, 120) == 120
    assert clamp(20, 60, 120) == 60


def test_deadband_behavior():
    angle = compute_target_angle(90, 0.05, kp=18.0, deadband=0.10, min_angle=60, max_angle=120)
    assert angle == 90


def test_target_angle_calculation():
    angle = compute_target_angle(90, 0.5, kp=18.0, deadband=0.10, min_angle=60, max_angle=120)
    assert angle > 90
