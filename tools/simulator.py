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

from sentinel.algorithm import SAFE_TTC_S, Thresholds, alert_level, ttc_seconds  # noqa: E402

LIMITS = Thresholds()
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
            event = {
                "max_level": 0,
                "max_speed": 0.0,
                "min_ttc": SAFE_TTC_S,
                "min_dist": 999.0,
            }
            start = time.time()
            attentive = random.random() < 0.7
            while distance > 8:
                ttc = ttc_seconds(distance, speed)
                level = alert_level(ttc, speed, *LIMITS.scaled())
                sequence += 1
                publish(
                    client,
                    1,
                    "alert",
                    {
                        "level": level,
                        "mode": 1,
                        "speed": round(speed + random.gauss(0, 0.8), 1),
                        "dist": round(distance, 1),
                        "ttc": round(ttc, 2),
                        "seq": sequence,
                    },
                )
                event["max_level"] = max(int(event["max_level"]), level)
                event["max_speed"] = max(float(event["max_speed"]), speed)
                event["min_ttc"] = min(float(event["min_ttc"]), ttc)
                event["min_dist"] = min(float(event["min_dist"]), distance)
                time.sleep(0.1)
                distance -= speed / 3.6 * 0.1
                if level >= 1 and attentive:
                    speed = max(15, speed * 0.97)
                    if distance < random.uniform(25, 40):
                        break
            event["duration_ms"] = int((time.time() - start) * 1000)
            rounded = {
                key: round(value, 2) if isinstance(value, float) else value
                for key, value in event.items()
            }
            publish(client, 1, "event", rounded)
            sequence += 1
            publish(
                client,
                1,
                "alert",
                {"level": 0, "mode": 1, "speed": 0, "dist": 0, "ttc": 99, "seq": sequence},
            )
            print("车辆通过", rounded)
            time.sleep(random.uniform(2, 6))
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
