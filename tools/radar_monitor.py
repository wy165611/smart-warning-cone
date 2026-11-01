"""HLK-LD2451 雷达串口调试工具（电脑直连 USB-TTL）。

实时打印每个目标的角度、距离、方向、速度、信噪比，并可存 CSV。

接线：USB-TTL 5V→雷达 5V，GND→GND，TX→雷达 RX，RX→雷达 TX

    pip install pyserial
    python tools/radar_monitor.py COM5
    python tools/radar_monitor.py /dev/ttyUSB0 --csv test.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sentinel.radar import FrameParser  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    try:
        import serial
    except ImportError:
        print("需要 pyserial：pip install pyserial", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="打印 HLK-LD2451 串口目标")
    parser.add_argument("port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--csv")
    args = parser.parse_args(argv)

    port = serial.Serial(args.port, args.baud, timeout=0.1)
    csv_file = None
    writer = None
    frames = FrameParser()
    try:
        if args.csv:
            csv_file = open(args.csv, "w", newline="", encoding="utf-8")
            writer = csv.writer(csv_file)
            writer.writerow(["time", "angle", "dist_m", "approach", "speed_kmh", "snr"])
        while True:
            for frame in frames.feed(port.read(port.in_waiting or 1)):
                stamp = time.time()
                if not frame.targets:
                    print("无目标")
                for target in frame.targets:
                    direction = "靠近" if target.approaching else "远离"
                    print(
                        f"角度{target.angle_deg:+3d}°  距离{target.dist_m:3d}m  "
                        f"{direction}  {target.speed_kmh:3d}km/h  SNR{target.snr}"
                    )
                    if writer is not None:
                        writer.writerow(
                            [
                                f"{stamp:.2f}",
                                target.angle_deg,
                                target.dist_m,
                                int(target.approaching),
                                target.speed_kmh,
                                target.snr,
                            ]
                        )
                if csv_file is not None:
                    csv_file.flush()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        if csv_file is not None:
            csv_file.close()
        port.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
