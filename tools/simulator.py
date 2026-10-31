"""
无硬件模拟器：模拟 1 个哨兵 + 3 个联动锥桶 + 1 个工人报警器，向 MQTT 发数据。
用来在硬件到货前调试后端与网页看板。

    pip install paho-mqtt
    python simulator.py --host localhost
"""
import argparse
import json
import random
import time

import paho.mqtt.client as mqtt

TTC1, TTC2, LIMIT = 5.0, 2.5, 40


def level_of(ttc, v):
    if ttc < TTC2:
        return 2
    if ttc < TTC1 or v > LIMIT * 1.2:
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    a = ap.parse_args()
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.connect(a.host, a.port)
    c.loop_start()
    pub = lambda node, kind, d: c.publish(f"cone/{node}/{kind}", json.dumps(d))  # noqa: E731

    seq, last_hb = 0, 0
    print("模拟中，Ctrl+C 退出")
    while True:
        # 心跳
        if time.time() - last_hb > 5:
            for nid, t in [(1, 1), (2, 2), (3, 2), (4, 2), (20, 3)]:
                pub(nid, "heartbeat", {"type": t, "batt": round(random.uniform(3.7, 4.1), 2), "mode": 1, "level": 0, "rssi": -random.randint(40, 70)})
            last_hb = time.time()

        # 一辆车从 100 m 驶来
        v = random.choice([30, 38, 45, 55, 65, 80]) + random.uniform(-3, 3)
        d = 100.0
        ev = {"max_level": 0, "max_speed": 0, "min_ttc": 99, "min_dist": 999}
        start = time.time()
        attentive = random.random() < 0.7      # 70% 司机看到预警会减速并变道
        while d > 8:
            ttc = d / (v / 3.6)
            lv = level_of(ttc, v)
            seq += 1
            pub(1, "alert", {"level": lv, "mode": 1, "speed": round(v + random.gauss(0, 0.8), 1), "dist": round(d, 1), "ttc": round(ttc, 2), "seq": seq})
            ev["max_level"] = max(ev["max_level"], lv)
            ev["max_speed"] = max(ev["max_speed"], v)
            ev["min_ttc"] = min(ev["min_ttc"], ttc)
            ev["min_dist"] = min(ev["min_dist"], d)
            time.sleep(0.1)
            d -= v / 3.6 * 0.1
            if lv >= 1 and attentive:            # 注意到预警：减速，并在 30 m 左右变道离开雷达视野
                v = max(15, v * 0.97)
                if d < random.uniform(25, 40):
                    break
        ev["duration_ms"] = int((time.time() - start) * 1000)
        ev = {k: round(x, 2) if isinstance(x, float) else x for k, x in ev.items()}
        pub(1, "event", ev)
        pub(1, "alert", {"level": 0, "mode": 1, "speed": 0, "dist": 0, "ttc": 99, "seq": seq + 1})
        print("车辆通过", ev)
        time.sleep(random.uniform(2, 6))


if __name__ == "__main__":
    main()
