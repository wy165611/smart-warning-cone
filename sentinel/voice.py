"""ASRPRO 与哨兵之间的 4 字节串口帧：AA 55 CMD SUM。"""

from __future__ import annotations

HDR1 = 0xAA
HDR2 = 0x55

CMD_START_WORK = 0x01
CMD_STOP_WORK = 0x02
CMD_LEFT = 0x03
CMD_RIGHT = 0x04
CMD_RAIN_ON = 0x05
CMD_RAIN_OFF = 0x06
CMD_NIGHT_ON = 0x07
CMD_NIGHT_OFF = 0x08
CMD_BATTERY = 0x09
CMD_TEST = 0x0A
REPLY_BATT_OK = 0x81
REPLY_BATT_LOW = 0x82


def checksum(cmd: int) -> int:
    return (HDR1 + HDR2 + (cmd & 0xFF)) & 0xFF


def encode(cmd: int) -> bytes:
    command = cmd & 0xFF
    return bytes((HDR1, HDR2, command, checksum(command)))


def decode(frame: bytes) -> int | None:
    """校验通过时返回命令字，否则返回 None。"""
    if len(frame) != 4 or frame[0] != HDR1 or frame[1] != HDR2:
        return None
    if frame[3] != checksum(frame[2]):
        return None
    return frame[2]


class VoiceStream:
    """逐字节解析语音帧，同步规则与哨兵 pollVoice() 相同。

    第二字节不是 0x55 时，若它自己是 0xAA，则把它当作下一帧的帧头，
    避免 AA AA 55 … 这种重叠把真正的命令丢掉。
    """

    def __init__(self) -> None:
        self._buf = [0, 0, 0, 0]
        self._idx = 0

    def feed(self, data: bytes) -> list[int]:
        commands: list[int] = []
        for byte in data:
            if self._idx == 0 and byte != HDR1:
                continue
            if self._idx == 1 and byte != HDR2:
                self._idx = 1 if byte == HDR1 else 0
                continue
            self._buf[self._idx] = byte
            self._idx += 1
            if self._idx == 4:
                self._idx = 0
                if (self._buf[0] + self._buf[1] + self._buf[2]) & 0xFF == self._buf[3]:
                    commands.append(self._buf[2])
        return commands
