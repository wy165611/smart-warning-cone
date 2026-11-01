"""预警算法的纯函数参考实现。

判定与 firmware/sentinel/sentinel.ino 的 processRadar 一致。
阈值是设计默认值，不是外场标定结果。修改 firmware/common/config.h 时请同步这里的常量。
"""

from __future__ import annotations

from dataclasses import dataclass

TTC_LEVEL1_S = 5.0
TTC_LEVEL2_S = 2.5
SPEED_LIMIT_KMH = 40.0
OVERSPEED_RATIO = 1.2
RAIN_FACTOR = 1.4
NIGHT_FACTOR = 1.2
CONFIRM_FRAMES = 3
MIN_TRACK_SPEED_KMH = 5.0
MAX_TRACK_DIST_M = 100.0
SAFE_TTC_S = 99.0

LEVEL_SAFE = 0
LEVEL_WARN = 1
LEVEL_DANGER = 2


@dataclass(frozen=True)
class Thresholds:
    level1_s: float = TTC_LEVEL1_S
    level2_s: float = TTC_LEVEL2_S
    speed_limit_kmh: float = SPEED_LIMIT_KMH
    overspeed_ratio: float = OVERSPEED_RATIO
    rain_factor: float = RAIN_FACTOR
    night_factor: float = NIGHT_FACTOR

    def scaled(self, *, rain: bool = False, night: bool = False) -> tuple[float, float]:
        factor = 1.0
        if rain:
            factor *= self.rain_factor
        if night:
            factor *= self.night_factor
        return self.level1_s * factor, self.level2_s * factor


def ttc_seconds(dist_m: float, speed_kmh: float) -> float:
    """碰撞时间（秒）= 距离(m) / 速度(m/s)。速度过低时返回 SAFE_TTC_S，避免除零。"""
    if speed_kmh <= 1.0:
        return SAFE_TTC_S
    return dist_m / (speed_kmh / 3.6)


def alert_level(
    ttc_s: float,
    speed_kmh: float,
    t1: float,
    t2: float,
    thresholds: Thresholds | None = None,
) -> int:
    """0 安全，1 一级，2 二级。比较符与固件相同：严格小于阈值才升级。"""
    limits = thresholds or Thresholds()
    if ttc_s < t2:
        return LEVEL_DANGER
    if ttc_s < t1 or speed_kmh > limits.speed_limit_kmh * limits.overspeed_ratio:
        return LEVEL_WARN
    return LEVEL_SAFE


def update_confirm(
    level: int,
    confirm_count: int,
    want: int,
    confirm_frames: int = CONFIRM_FRAMES,
) -> tuple[int, int]:
    """升级需要连续 confirm_frames 帧；降级立即生效。"""
    if want > LEVEL_SAFE:
        confirm_count += 1
    else:
        confirm_count = 0
    if confirm_count >= confirm_frames or want < level:
        level = want
    return level, confirm_count


@dataclass(frozen=True)
class Track:
    dist_m: float
    speed_kmh: float
    approaching: bool


def select_threat(
    targets: list[Track],
    *,
    min_speed_kmh: float = MIN_TRACK_SPEED_KMH,
    max_dist_m: float = MAX_TRACK_DIST_M,
) -> Track | None:
    """在靠近、速度和距离都合格的目标里，选 TTC 最小的一个。"""
    best: Track | None = None
    best_ttc = SAFE_TTC_S
    for target in targets:
        if not target.approaching:
            continue
        if target.speed_kmh < min_speed_kmh or target.dist_m > max_dist_m:
            continue
        ttc = ttc_seconds(target.dist_m, target.speed_kmh)
        if best is None or ttc < best_ttc:
            best = target
            best_ttc = ttc
    return best


class Kalman1D:
    """一维常值卡尔曼滤波，与 firmware/sentinel/kalman.h 相同。"""

    def __init__(self, q: float = 0.5, r: float = 4.0) -> None:
        self.q = q
        self.r = r
        self._x = 0.0
        self._p = 1.0
        self._ready = False

    def reset(self) -> None:
        self._ready = False

    def update(self, measurement: float) -> float:
        if not self._ready:
            self._x = measurement
            self._p = self.r
            self._ready = True
            return self._x
        self._p += self.q
        gain = self._p / (self._p + self.r)
        self._x += gain * (measurement - self._x)
        self._p *= 1 - gain
        return self._x
