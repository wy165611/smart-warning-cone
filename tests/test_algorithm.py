from sentinel.algorithm import (
    MODE_NIGHT,
    MODE_RAIN,
    MODE_WORKING,
    Kalman1D,
    ThreatTracker,
    Thresholds,
    Track,
    alert_level,
    elapsed_ms,
    select_threat,
    ttc_seconds,
    update_confirm,
)
from sentinel.report import format_fixed, format_kmh


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
    level, count = 0, 0
    for _ in range(10):
        level, count = update_confirm(level, count, 1)
    assert (level, count) == (1, 3)


def _danger() -> list[Track]:
    return [Track(20, 60, True)]


def test_release_holds_until_the_window_expires_and_then_zeroes_the_live_state() -> None:
    tracker = ThreatTracker()
    step = None
    for stamp in (0, 100, 200):
        step = tracker.on_radar([_danger()], stamp)
    assert step is not None
    assert step.level == 2
    assert tracker.on_radar([], 200 + 1500).closed is None
    assert tracker.on_radar([], 200 + 1500).level == 2
    done = tracker.on_radar([], 200 + 1501)
    assert done.level == 0
    assert done.dist_m == 0
    assert done.speed_kmh == 0
    assert done.closed is not None
    assert done.closed.max_level == 2
    assert done.closed.duration_ms == 1701


def test_release_timer_survives_millis_wrap() -> None:
    near = 0xFFFFFFF0
    tracker = ThreatTracker()
    for _ in range(3):
        step = tracker.on_radar([_danger()], near)
    assert step.level == 2
    wrapped = (near + 100) & 0xFFFFFFFF
    assert elapsed_ms(wrapped, near) == 100
    held = tracker.on_radar([], wrapped)
    assert held.level == 2
    assert held.closed is None


def test_filtered_safe_reading_drops_the_level_without_closing_the_passage() -> None:
    tracker = ThreatTracker()
    for stamp in (0, 100, 200):
        tracker.on_radar([_danger()], stamp)
    # 滤波还停在近处，一帧 90 m 只把二级拉到一级，不会结束这次通过。
    first = tracker.on_radar([[Track(90, 20, True)]], 300)
    assert first.level == 1
    assert first.closed is None
    second = tracker.on_radar([[Track(90, 20, True)]], 400)
    assert second.level == 0
    assert second.closed is None
    assert tracker.on_radar([], 400 + 1500).closed is None
    done = tracker.on_radar([], 400 + 1501)
    assert done.closed is not None
    assert done.closed.max_level == 2


def test_idle_mode_does_not_prime_confirmation_or_record_a_passage() -> None:
    tracker = ThreatTracker(mode=0)
    for stamp in (0, 100, 200):
        step = tracker.on_radar([_danger()], stamp)
        assert step.level == 0
        assert step.closed is None
    tracker.set_mode(MODE_WORKING, 300)
    assert tracker.on_radar([_danger()], 400).level == 0
    assert tracker.on_radar([_danger()], 500).level == 0
    assert tracker.on_radar([_danger()], 600).level == 2


def test_leaving_work_mode_closes_the_passage_once() -> None:
    tracker = ThreatTracker()
    for stamp in (0, 100, 200):
        tracker.on_radar([_danger()], stamp)
    step = tracker.set_mode(0, 250)
    assert step.level == 0
    assert step.dist_m == 0
    assert step.closed is not None
    assert step.closed.max_level == 2
    assert step.closed.duration_ms == 250
    assert tracker.on_radar([_danger()], 300).closed is None
    assert tracker.on_radar([_danger()], 300).level == 0


def test_rain_and_night_change_the_confirmed_level() -> None:
    dry = ThreatTracker()
    wet = ThreatTracker(mode=MODE_WORKING | MODE_RAIN | MODE_NIGHT)
    # 30 m、40 km/h：TTC = 2.7 s。干燥时只到一级；雨夜阈值放大后进入二级。
    sample = [[Track(30, 40, True)]]
    dry_step = wet_step = None
    for stamp in (0, 100, 200):
        dry_step = dry.on_radar(sample, stamp)
        wet_step = wet.on_radar(sample, stamp)
    assert dry_step is not None and wet_step is not None
    assert dry_step.level == 1
    assert wet_step.level == 2


def test_does_not_select_target_at_the_firmware_ttc_ceiling() -> None:
    # 36 km/h = 10 m/s，990 m 的 TTC 恰好是 99 s，固件的初值比较是严格小于。
    same = Track(990, 36, True)
    closer = Track(980, 36, True)
    assert select_threat([same], min_speed_kmh=5, max_dist_m=1000) is None
    assert select_threat([same, closer], min_speed_kmh=5, max_dist_m=1000) == closer


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
    assert format_fixed(48.25, 1) == "48.3"
    assert format_fixed(1.25, 1) == "1.3"


def test_kalman_first_sample_is_measurement_then_pulls_toward_next() -> None:
    filt = Kalman1D(0.5, 4.0)
    assert filt.update(10) == 10
    nxt = filt.update(14)
    gain = 4.5 / 8.5
    assert nxt == 10 + gain * 4
    filt.reset()
    assert filt.update(3) == 3
