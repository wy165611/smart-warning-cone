"""ESP-NOW 序号去重，与 firmware/common/protocol.h 的 seqIsNew() 相同。

联动锥桶、工人端和网关都调用这个函数。工人端若不做去重，
迟到的中继副本会把已经解除的告警重新打开。
"""

from __future__ import annotations

REORDER_WINDOW = 64


class SeqFilter:
    """按发送者记住最近一次接受的序号。

    - 同号丢弃（原始包和中继副本序号相同）；
    - 比上次小、但相差不到 REORDER_WINDOW，视为迟到的副本，丢弃；
    - 相差更多，视为对方重启后重新起号，接受；
    - 从没见过的发送者，第一包无论序号是多少都接受（包括 0）。
    """

    def __init__(self, window: int = REORDER_WINDOW) -> None:
        self.window = window
        self._last: dict[int, int] = {}

    def accept(self, node_id: int, seq: int) -> bool:
        seq &= 0xFFFFFFFF
        last = self._last.get(node_id)
        if last is not None:
            if seq == last:
                return False
            if seq < last and last - seq < self.window:
                return False
        self._last[node_id] = seq
        return True
