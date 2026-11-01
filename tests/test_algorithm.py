from sentinel.algorithm import (
    Kalman1D,
    Thresholds,
    Track,
    alert_level,
    select_threat,
    ttc_seconds,
    update_confirm,
)
from sentinel.report import format_kmh


def test_ttc_matches_distance_over_speed() -> None:
    # 60 km/h = 16.666... m/s；40 m 需要 2.4 s
    assert ttc_seconds(40, 60) == 2.4
    assert ttc_seconds(10, 0) == 99.0


def test_level_boundaries_match_firmware() -> None:
    limits = Thresholds()
    t1, t2 = limits.scaled()
    assert alert_level(2.49, 30, t1, t2, limits) == 2
    assert alert_level(2.5, 30, t1, t2, limits) == 1
    assert alert_level(4.99, 30, t1, t2, limits) == 1
    assert alert_level(5.0, 30, t1, t2, limits) == 0
    assert alert_level(10, 48.0, t1, t2, limits) == 0
    assert alert_level(10, 48.1, t1, t2, limits) == 1


def test_rain_and_night_stack() -> None:
    t1, t2 = Thresholds().scaled(rain=True, night=True)
    assert t1 == 5.0 * 1.4 * 1.2
    assert t2 == 2.5 * 1.4 * 1.2


def test_confirm_upgrades_after_three_frames_and_downgrades_immediately() -> None:
    level, count = 0, 0
    level, count = update_confirm(level, count, 1)
    assert (level, count) == (0, 1)
    level, count = update_confirm(level, count, 1)
    assert (level, count) == (0, 2)
    level, count = update_confirm(level, count, 1)
    assert (level, count) == (1, 3)
    level, count = update_confirm(level, count, 2)
    assert level == 2
    level, count = update_confirm(level, count, 0)
    assert (level, count) == (0, 0)


def test_selects_smallest_ttc_and_ignores_receding_or_slow_targets() -> None:
    chosen = select_threat(
        [
            Track(80, 40, True),
            Track(20, 40, False),
            Track(30, 4, True),
            Track(40, 60, True),
        ]
    )
    assert chosen == Track(40, 60, True)
    assert select_threat([Track(10, 3, True)]) is None


def test_report_speed_rounds_half_up_like_the_dashboard() -> None:
    assert format_kmh(46.5) == "47"
    assert format_kmh(46.4) == "46"


def test_kalman_first_sample_is_measurement_then_pulls_toward_next() -> None:
    filt = Kalman1D(0.5, 4.0)
    assert filt.update(10) == 10
    nxt = filt.update(14)
    gain = 4.5 / 8.5
    assert nxt == 10 + gain * 4
    filt.reset()
    assert filt.update(3) == 3
