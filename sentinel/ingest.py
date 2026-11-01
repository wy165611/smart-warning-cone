"""把 MQTT JSON 写入数据库。坏消息返回错误字符串，不抛给回调线程。"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

MAX_PAYLOAD_BYTES = 4096
KINDS = frozenset({"heartbeat", "alert", "event", "config"})


def _number(data: dict[str, Any], key: str, cast: type[float] | type[int]) -> float | int:
    if key not in data:
        raise ValueError(f"missing {key}")
    value = data[key]
    if isinstance(value, bool) or value is None:
        raise ValueError(f"bad {key}")
    return cast(value)


def _optional_number(
    data: dict[str, Any], key: str, cast: type[float] | type[int]
) -> float | int | None:
    if key not in data or data[key] is None:
        return None
    return _number(data, key, cast)


def ingest(conn: sqlite3.Connection, topic: str, payload: bytes | str, now: float) -> str | None:
    """成功返回 None。调用方负责提交事务。"""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "cone" or parts[2] not in KINDS:
        return "bad topic"
    try:
        node = int(parts[1])
    except ValueError:
        return "bad node"
    if node < 0 or node > 255:
        return "bad node"
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    if len(raw) > MAX_PAYLOAD_BYTES:
        return "payload too large"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "bad json"
    if not isinstance(data, dict):
        return "payload not object"
    kind = parts[2]
    try:
        if kind == "heartbeat":
            _heartbeat(conn, node, data, now)
        elif kind == "alert":
            _alert(conn, node, data, now)
        elif kind == "event":
            _event(conn, node, data, now)
        else:
            _config(conn, node, data)
    except (ValueError, TypeError, OverflowError) as exc:
        return str(exc)
    return None


def _heartbeat(conn: sqlite3.Connection, node: int, data: dict[str, Any], now: float) -> None:
    conn.execute(
        "INSERT INTO nodes(id,type,batt,mode,level,rssi,last_seen) VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET type=excluded.type,batt=excluded.batt,mode=excluded.mode,"
        "level=excluded.level,rssi=excluded.rssi,last_seen=excluded.last_seen",
        (
            node,
            _optional_number(data, "type", int),
            _optional_number(data, "batt", float),
            _optional_number(data, "mode", int),
            _optional_number(data, "level", int),
            _optional_number(data, "rssi", int),
            now,
        ),
    )


def _alert(conn: sqlite3.Connection, node: int, data: dict[str, Any], now: float) -> None:
    level = int(_number(data, "level", int))
    speed = float(_number(data, "speed", float))
    dist = float(_number(data, "dist", float))
    ttc = float(_number(data, "ttc", float))
    mode = _optional_number(data, "mode", int)
    conn.execute(
        "INSERT INTO alerts(ts,node,level,speed,dist,ttc) VALUES(?,?,?,?,?,?)",
        (now, node, level, speed, dist, ttc),
    )
    conn.execute(
        "INSERT INTO nodes(id,type,level,mode,last_seen) VALUES(?,1,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET level=excluded.level,mode=excluded.mode,"
        "last_seen=excluded.last_seen",
        (node, level, mode, now),
    )


def _event(conn: sqlite3.Connection, node: int, data: dict[str, Any], now: float) -> None:
    conn.execute(
        "INSERT INTO events(ts,node,max_level,max_speed,min_ttc,min_dist,duration_ms) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            now,
            node,
            int(_number(data, "max_level", int)),
            float(_number(data, "max_speed", float)),
            float(_number(data, "min_ttc", float)),
            float(_number(data, "min_dist", float)),
            int(_number(data, "duration_ms", int)),
        ),
    )


def _config(conn: sqlite3.Connection, node: int, data: dict[str, Any]) -> None:
    mode = int(_number(data, "mode", int))
    conn.execute(
        "INSERT INTO nodes(id, mode) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET mode=excluded.mode",
        (node, mode),
    )
