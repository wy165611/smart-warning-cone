"""把 firmware/common/ 下的 config.h、protocol.h 同步到每个固件目录。

Arduino IDE 只编译草图目录内的文件，所以每个目录都放了一份副本。
修改参数时只改 firmware/common/ 里的文件，然后运行：

    python tools/sync_common.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SKETCHES = ("sentinel", "follower", "worker", "gateway")
HEADERS = ("config.h", "protocol.h")


def sync_common(firmware_root: Path) -> list[str]:
    common = firmware_root / "common"
    copied: list[str] = []
    for sketch in SKETCHES:
        for name in HEADERS:
            source = common / name
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = firmware_root / sketch / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(f"common/{name} -> {sketch}/{name}")
    return copied


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "firmware"
    try:
        for line in sync_common(root):
            print(line)
    except FileNotFoundError as exc:
        print(f"缺少公共头文件：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
