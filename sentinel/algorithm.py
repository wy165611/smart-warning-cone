"""预警算法的参考实现。

单帧判定与 firmware/sentinel/sentinel.ino 的 processRadar 一致。
ThreatTracker 覆盖同一文件里的确认、解除、非作业模式和事件收口。
阈值是设计默认值，不是外场标定结果。修改 firmware/common/config.h
或 protocol.h 里的模式位时，请同步这里的常量。
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
RELEASE_MS = 1500

# 与 firmware/common/protocol.h 的模式位一致
MODE_WORKING = 0x01
MODE_LEFT = 0x02
MODE_RAIN = 0x04
MODE_NIGHT = 0x08

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
    """升级需要连续 confirm_frames 帧；降级立即生效。

    确认计数停在 confirm_frames，避免长时间跟踪时一直加到溢出。
    计数一旦达到阈值，后续帧的 want 会立刻成为等级，升到更高档不需要重新计满。
    """
    if want > LEVEL_SAFE:
        confirm_count += 1
        if confirm_frames > 0 and confirm_count > confirm_frames:
            confirm_count = confirm_frames
    else:
        confirm_count = 0
    if confirm_count >= confirm_frames or want < level:
        level = want
    return level, confirm_count


def elapsed_ms(now_ms: int, then_ms: int) -> int:
    """与固件 uint32 的 millis() 减法一致，时钟回绕后仍是经过的毫秒数。"""
    return (int(now_ms) - int(then_ms)) & 0xFFFFFFFF


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
        # 固件初值是 99，并且只用“严格小于”，所以 TTC 恰好为 99 s 的目标不会被选中。
        if ttc < best_ttc:
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


@dataclass(frozen=True)
class Passage:
    """一次车辆通过结束时上报的事件。字段与 EventPkt 对应。"""

    max_level: int
    max_speed: float
    min_ttc: float
    min_dist: float
    duration_ms: int


@dataclass(frozen=True)
class RadarStep:
    level: int
    ttc_s: float
    dist_m: float
    speed_kmh: float
    closed: Passage | None = None


class ThreatTracker:
    """哨兵固件 processRadar、releaseIfIdle、clearThreat 的参考实现。

    非作业模式只丢弃目标：不累计确认、不开事件，并立即解除已有告警。
    作业中目标消失超过 release_ms 才解除；解除或结束作业时实时速度、距离清零，
    本次通过的极值留在 Passage 里。比较时刻使用 uint32 毫秒时钟。
    """

    def __init__(
        self,
        thresholds: Thresholds | None = None,
        *,
        mode: int = MODE_WORKING,
        release_ms: int = RELEASE_MS,
        confirm_frames: int = CONFIRM_FRAMES,
        min_speed_kmh: float = MIN_TRACK_SPEED_KMH,
        max_dist_m: float = MAX_TRACK_DIST_M,
    ) -> None:
        self.thresholds = thresholds or Thresholds()
        self.mode = mode
        self.release_ms = release_ms
        self.confirm_frames = confirm_frames
        self.min_speed_kmh = min_speed_kmh
        self.max_dist_m = max_dist_m
        self.level = LEVEL_SAFE
        self.confirm = 0
        self.ttc_s = SAFE_TTC_S
        self.dist_m = 0.0
        self.speed_kmh = 0.0
        self._last_hit: int | None = None
        self._in_event = False
        self._event_start = 0
        self._max_level = LEVEL_SAFE
        self._max_speed = 0.0
        self._min_ttc = SAFE_TTC_S
        self._min_dist = 999.0
        self._kf_dist = Kalman1D()
        self._kf_speed = Kalman1D()

    @property
    def working(self) -> bool:
        return bool(self.mode & MODE_WORKING)

    def set_mode(self, mode: int, now_ms: int) -> RadarStep:
        """切换模式。离开作业模式时立即收口，与语音“结束作业”相同。"""
        self.mode = mode
        closed = self._disarm(now_ms) if not self.working else None
        return self._step(closed)

    def on_radar(self, frames: list[list[Track]], now_ms: int) -> RadarStep:
        """处理同一时刻读到的若干帧，然后按时间决定要不要解除。"""
        if not self.working:
            return self._step(self._disarm(now_ms))
        for targets in frames:
            threat = select_threat(
                targets,
                min_speed_kmh=self.min_speed_kmh,
                max_dist_m=self.max_dist_m,
            )
            if threat is None:
                continue
            self._last_hit = now_ms
            self.dist_m = self._kf_dist.update(threat.dist_m)
            self.speed_kmh = self._kf_speed.update(threat.speed_kmh)
            self.ttc_s = ttc_seconds(self.dist_m, self.speed_kmh)
            t1, t2 = self.thresholds.scaled(
                rain=bool(self.mode & MODE_RAIN),
                night=bool(self.mode & MODE_NIGHT),
            )
            want = alert_level(self.ttc_s, self.speed_kmh, t1, t2, self.thresholds)
            self.level, self.confirm = update_confirm(
                self.level, self.confirm, want, self.confirm_frames
            )
            self._observe(now_ms)
        return self._step(self._release_if_idle(now_ms))

    def _step(self, closed: Passage | None) -> RadarStep:
        return RadarStep(self.level, self.ttc_s, self.dist_m, self.speed_kmh, closed)

    def _observe(self, now_ms: int) -> None:
        if not self._in_event:
            self._in_event = True
            self._event_start = now_ms
            self._max_level = LEVEL_SAFE
            self._max_speed = 0.0
            self._min_ttc = SAFE_TTC_S
            self._min_dist = 999.0
        if self.level > self._max_level:
            self._max_level = self.level
        if self.speed_kmh > self._max_speed:
            self._max_speed = self.speed_kmh
        if self.ttc_s < self._min_ttc:
            self._min_ttc = self.ttc_s
        if self.dist_m < self._min_dist:
            self._min_dist = self.dist_m

    def _release_if_idle(self, now_ms: int) -> Passage | None:
        if self.level == LEVEL_SAFE and not self._in_event:
            return None
        if self._last_hit is None:
            return None
        if elapsed_ms(now_ms, self._last_hit) <= self.release_ms:
            return None
        return self._disarm(now_ms)

    def _disarm(self, now_ms: int) -> Passage | None:
        closed = self._close(now_ms)
        self.confirm = 0
        self.level = LEVEL_SAFE
        self.ttc_s = SAFE_TTC_S
        self.dist_m = 0.0
        self.speed_kmh = 0.0
        self._kf_dist.reset()
        self._kf_speed.reset()
        return closed

    def _close(self, now_ms: int) -> Passage | None:
        if not self._in_event:
            return None
        passage = Passage(
            max_level=self._max_level,
            max_speed=self._max_speed,
            min_ttc=self._min_ttc,
            min_dist=self._min_dist,
            duration_ms=elapsed_ms(now_ms, self._event_start),
        )
        self._in_event = False
        return passage
