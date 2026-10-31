"""
HLK-LD2451 雷达串口调试工具（电脑直连 USB-TTL）
实时打印每个目标的角度、距离、方向、速度、信噪比，并可存 CSV 用于精度测试。

接线：USB-TTL 5V→雷达 5V，GND→GND，TX→雷达 RX，RX→雷达 TX
    pip install pyserial
    python radar_monitor.py COM5            # Windows
    python radar_monitor.py /dev/ttyUSB0 --csv test.csv
"""
import argparse
import csv
import time

import serial

HDR, TAIL = b"\xf4\xf3\xf2\xf1", b"\xf8\xf7\xf6\xf5"


def frames(ser):
    buf = b""
    while True:
        buf += ser.read(ser.in_waiting or 1)
        while True:
            i = buf.find(HDR)
            if i < 0 or len(buf) < i + 6:
                break
            n = buf[i + 4] | (buf[i + 5] << 8)
            end = i + 6 + n + 4
            if len(buf) < end:
                break
            if buf[end - 4:end] == TAIL:
                yield buf[i + 6:i + 6 + n]
            buf = buf[end:]


def parse(d):
    if len(d) < 2:
        return []
    out = []
    for k in range(d[0]):
        t = d[2 + 5 * k: 7 + 5 * k]
        if len(t) < 5:
            break
        out.append({"angle": t[0] - 0x80, "dist": t[1], "approach": t[2] == 1, "speed": t[3], "snr": t[4]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--csv")
    a = ap.parse_args()
    ser = serial.Serial(a.port, a.baud, timeout=0.1)
    w = None
    if a.csv:
        f = open(a.csv, "w", newline="", encoding="utf-8")
        w = csv.writer(f)
        w.writerow(["time", "angle", "dist_m", "approach", "speed_kmh", "snr"])
    for d in frames(ser):
        ts = time.time()
        targets = parse(d)
        if not targets:
            print("无目标")
        for t in targets:
            print(f"角度{t['angle']:+3d}°  距离{t['dist']:3d}m  {'靠近' if t['approach'] else '远离'}  {t['speed']:3d}km/h  SNR{t['snr']}")
            if w:
                w.writerow([f"{ts:.2f}", t["angle"], t["dist"], int(t["approach"]), t["speed"], t["snr"]])


if __name__ == "__main__":
    main()
