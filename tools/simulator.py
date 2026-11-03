"""无硬件模拟器：1 个哨兵 + 3 个联动锥桶 + 1 个工人报警器，向 MQTT 发数据。

pip install paho-mqtt
python tools/simulator.py --host localhost
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt  # noqa: E402

from sentinel.algorithm import MODE_WORKING, RELEASE_MS, ThreatTracker, Track  # noqa: E402

NODES = ((1, 1), (2, 2), (3, 2), (4, 2), (20, 3))


def publish(client: mqtt.Client, node: int, kind: str, payload: dict[str, object]) -> None:
    client.publish(f"cone/{node}/{kind}", json.dumps(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="向 MQTT 发送一套作业区的模拟数据")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args(argv)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(args.host, args.port)
    except OSError as exc:
        print(f"无法连接 MQTT {args.host}:{args.port}：{exc}")
        print("请先启动 broker，例如在 server 目录执行 docker compose up mqtt")
        return 1
    client.loop_start()
    sequence = 0
    last_heartbeat = 0.0
    print("模拟中，Ctrl+C 退出")
    try:
        while True:
            now = time.time()
            if now - last_heartbeat > 5:
                for node_id, node_type in NODES:
                    publish(
                        client,
                        node_id,
                        "heartbeat",
                        {
                            "type": node_type,
                            "batt": round(random.uniform(3.7, 4.1), 2),
                            "mode": 1,
                            "level": 0,
                            "rssi": -random.randint(40, 70),
                        },
                    )
                last_heartbeat = time.time()

            speed = random.choice([30, 38, 45, 55, 65, 80]) + random.uniform(-3, 3)
            distance = 100.0
            # 逻辑时钟每帧 100 ms，与雷达有目标时的节拍相同；解除不额外空等 1.5 s。
            tracker = ThreatTracker(mode=MODE_WORKING)
            clock = 0
            attentive = random.random() < 0.7
            closed = None
            while distance > 8:
                clock += 100
                step = tracker.on_radar([[Track(distance, speed, True)]], clock)
                sequence += 1
                publish(
                    client,
                    1,
                    "alert",
                    {
                        "level": step.level,
                        "mode": MODE_WORKING,
                        "speed": round(step.speed_kmh, 1),
                        "dist": round(step.dist_m, 1),
                        "ttc": round(step.ttc_s, 2),
                        "seq": sequence,
                    },
                )
                if step.closed is not None:
                    closed = step.closed
                time.sleep(0.1)
                distance -= speed / 3.6 * 0.1
                if step.level >= 1 and attentive:
                    speed = max(15, speed * 0.97)
                    if distance < random.uniform(25, 40):
                        break
            clock += RELEASE_MS + 1
            step = tracker.on_radar([], clock)
            if step.closed is not None:
                closed = step.closed
            if closed is None:
                print("这次通过没有形成事件")
            else:
                payload = {
                    "max_level": closed.max_level,
                    "max_speed": round(closed.max_speed, 2),
                    "min_ttc": round(closed.min_ttc, 2),
                    "min_dist": round(closed.min_dist, 2),
                    "duration_ms": closed.duration_ms,
                }
                publish(client, 1, "event", payload)
                print("车辆通过", payload)
            sequence += 1
            publish(
                client,
                1,
                "alert",
                {
                    "level": step.level,
                    "mode": MODE_WORKING,
                    "speed": round(step.speed_kmh, 1),
                    "dist": round(step.dist_m, 1),
                    "ttc": round(step.ttc_s, 2),
                    "seq": sequence,
                },
            )
            time.sleep(random.uniform(2, 6))
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
