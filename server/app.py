"""
哨兵锥桶 · 后端服务
- 订阅 MQTT  cone/+/alert | heartbeat | event | config
- 存入 SQLite（events / alerts / nodes）
- 提供 REST API 与网页看板 (static/index.html)

运行：
    pip install -r requirements.txt
    python app.py             # 默认连接 localhost:1883，网页 http://localhost:8000
环境变量：MQTT_HOST, MQTT_PORT, DB_PATH
"""
import json
import os
import sqlite3
import threading
import time
from contextlib import closing

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DB_PATH = os.getenv("DB_PATH", "cone.db")
HERE = os.path.dirname(os.path.abspath(__file__))

db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db()) as c, c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes(
              id INTEGER PRIMARY KEY, type INTEGER, batt REAL, mode INTEGER,
              level INTEGER, rssi INTEGER, last_seen REAL);
            CREATE TABLE IF NOT EXISTS alerts(
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, node INTEGER,
              level INTEGER, speed REAL, dist REAL, ttc REAL);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, node INTEGER,
              max_level INTEGER, max_speed REAL, min_ttc REAL, min_dist REAL,
              duration_ms INTEGER);
            """
        )


# ---------------- MQTT ----------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    print("MQTT connected", reason_code)
    client.subscribe("cone/#")


def on_message(client, userdata, msg):
    try:
        _, node, kind = msg.topic.split("/")
        node = int(node)
        d = json.loads(msg.payload)
    except Exception as e:  # noqa: BLE001
        print("bad msg", msg.topic, e)
        return
    now = time.time()
    with db_lock, closing(db()) as c, c:
        if kind == "heartbeat":
            c.execute(
                "INSERT INTO nodes(id,type,batt,mode,level,rssi,last_seen) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET type=excluded.type,batt=excluded.batt,mode=excluded.mode,"
                "level=excluded.level,rssi=excluded.rssi,last_seen=excluded.last_seen",
                (node, d.get("type"), d.get("batt"), d.get("mode"), d.get("level"), d.get("rssi"), now),
            )
        elif kind == "alert":
            c.execute(
                "INSERT INTO alerts(ts,node,level,speed,dist,ttc) VALUES(?,?,?,?,?,?)",
                (now, node, d["level"], d["speed"], d["dist"], d["ttc"]),
            )
            c.execute(
                "INSERT INTO nodes(id,type,level,mode,last_seen) VALUES(?,1,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET level=excluded.level,mode=excluded.mode,last_seen=excluded.last_seen",
                (node, d["level"], d.get("mode"), now),
            )
        elif kind == "event":
            c.execute(
                "INSERT INTO events(ts,node,max_level,max_speed,min_ttc,min_dist,duration_ms) VALUES(?,?,?,?,?,?,?)",
                (now, node, d["max_level"], d["max_speed"], d["min_ttc"], d["min_dist"], d["duration_ms"]),
            )
        elif kind == "config":
            c.execute("UPDATE nodes SET mode=? WHERE id=?", (d["mode"], node))


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 30)
            break
        except OSError as e:
            print("MQTT connect failed, retry in 3s:", e)
            time.sleep(3)
    client.loop_start()


# ---------------- API ----------------
app = FastAPI(title="Sentinel Cone")
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


def rows(sql, args=()):
    with db_lock, closing(db()) as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))


@app.get("/api/nodes")
def nodes():
    now = time.time()
    out = rows("SELECT * FROM nodes ORDER BY id")
    for n in out:
        n["online"] = (now - (n["last_seen"] or 0)) < 15
    return out


@app.get("/api/alerts")
def alerts(minutes: int = 10):
    return rows("SELECT * FROM alerts WHERE ts > ? ORDER BY ts", (time.time() - minutes * 60,))


@app.get("/api/events")
def events(limit: int = 50):
    return rows("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))


@app.get("/api/stats")
def stats(hours: int = 24):
    since = time.time() - hours * 3600
    r = rows(
        "SELECT COUNT(*) AS total, SUM(max_level>=1) AS warn, SUM(max_level=2) AS danger, "
        "AVG(max_speed) AS avg_speed, MAX(max_speed) AS top_speed, MIN(min_ttc) AS min_ttc "
        "FROM events WHERE ts > ?",
        (since,),
    )[0]
    return {k: (v or 0) for k, v in r.items()}


@app.get("/api/report", response_class=PlainTextResponse)
def report(hours: int = 24):
    s = stats(hours)
    ev = rows("SELECT * FROM events WHERE ts > ? ORDER BY min_ttc LIMIT 5", (time.time() - hours * 3600,))
    lines = [
        f"作业区安全报告（最近 {hours} 小时）",
        f"通过车辆事件：{s['total']} 次；一级以上预警：{s['warn']} 次；二级预警：{s['danger']} 次",
        f"平均最高车速：{s['avg_speed']:.1f} km/h；最高车速：{s['top_speed']:.1f} km/h；最小 TTC：{s['min_ttc']:.2f} s",
        "最危险的 5 次接近：",
    ]
    for e in ev:
        t = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
        lines.append(f"  {t}  车速 {e['max_speed']:.0f} km/h  最小TTC {e['min_ttc']:.2f}s  最近 {e['min_dist']:.0f} m")
    return "\n".join(lines)


if __name__ == "__main__":
    init_db()
    start_mqtt()
    uvicorn.run(app, host="0.0.0.0", port=8000)
