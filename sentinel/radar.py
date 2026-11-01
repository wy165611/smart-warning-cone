"""HLK-LD2451 上报帧解析。

帧格式依据海凌科《LD2451 串口通信协议 V1.03》表 8、表 9：
帧头 F4 F3 F2 F1，长度 2 字节小端，帧尾 F8 F7 F6 F5。
每个目标 5 字节：角度（值减 0x80）、距离(m)、方向、速度(km/h)、信噪比。
方向按表 9：0x01 靠近，0x00 远离。该文档示例文字与表 9 不一致，实机需核对。
"""

from __future__ import annotations

from dataclasses import dataclass

HDR = b"\xf4\xf3\xf2\xf1"
TAIL = b"\xf8\xf7\xf6\xf5"
MAX_TARGETS = 5
MAX_PAYLOAD = 2 + 5 * MAX_TARGETS


@dataclass(frozen=True)
class RadarTarget:
    angle_deg: int
    dist_m: int
    approaching: bool
    speed_kmh: int
    snr: int


@dataclass(frozen=True)
class RadarFrame:
    count: int
    alarm: bool
    targets: tuple[RadarTarget, ...]


def parse_payload(payload: bytes) -> RadarFrame | None:
    """解析帧内数据。长度不足或没有目标时返回空帧；空字节串返回 None。"""
    if len(payload) < 2:
        return None
    count = payload[0]
    if count > MAX_TARGETS:
        count = MAX_TARGETS
    targets: list[RadarTarget] = []
    for index in range(count):
        start = 2 + 5 * index
        chunk = payload[start : start + 5]
        if len(chunk) < 5:
            break
        targets.append(
            RadarTarget(
                angle_deg=chunk[0] - 0x80,
                dist_m=chunk[1],
                approaching=chunk[2] == 0x01,
                speed_kmh=chunk[3],
                snr=chunk[4],
            )
        )
    return RadarFrame(count=len(targets), alarm=payload[1] == 0x01, targets=tuple(targets))


class FrameParser:
    """增量解析串口字节流。非法长度会丢弃 1 字节重新同步，缓冲不会无限增长。"""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[RadarFrame]:
        self._buf.extend(data)
        frames: list[RadarFrame] = []
        while True:
            start = self._buf.find(HDR)
            if start < 0:
                if len(self._buf) > len(HDR) - 1:
                    del self._buf[: -(len(HDR) - 1)]
                break
            if start > 0:
                del self._buf[:start]
            if len(self._buf) < 6:
                break
            length = self._buf[4] | (self._buf[5] << 8)
            if length > MAX_PAYLOAD:
                del self._buf[0]
                continue
            end = 6 + length + 4
            if len(self._buf) < end:
                break
            body = bytes(self._buf[6 : 6 + length])
            tail = bytes(self._buf[end - 4 : end])
            del self._buf[:end]
            if tail != TAIL:
                continue
            frame = parse_payload(body)
            if frame is not None:
                frames.append(frame)
        return frames
