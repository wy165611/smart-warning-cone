"""把 MQTT JSON 写入数据库。坏消息返回错误字符串，不抛给回调线程。"""

from __future__ import annotations

import json
import math
import sqlite3
from typing import Any

MAX_PAYLOAD_BYTES = 4096
KINDS = frozenset({"heartbeat", "alert", "event", "config"})
# 宽松上界，只挡住会写坏统计或看板的值。雷达实际量程远小于这些数。
_SPEED = (0.0, 500.0)
_DIST = (0.0, 2000.0)
_TTC = (0.0, 10000.0)
_BATT = (0.0, 10.0)
_RSSI = (-128, 127)
_DURATION = (0, 2**32 - 1)
_MODE = (0, 255)
_LEVELS = (0, 2)  # 只接受 0 安全 / 1 一级 / 2 二级


def _number(data: dict[str, Any], key: str, cast: type[float] | type[int]) -> float | int:
    if key not in data:
        raise ValueError(f"missing {key}")
    value = data[key]
    # bool 是 int 的子类，不能当成等级或速度。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"bad {key}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"bad {key}")
    try:
        number = cast(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"bad {key}") from None
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError(f"bad {key}")
    return number


def _bounded(
    data: dict[str, Any],
    key: str,
    cast: type[float] | type[int],
    bounds: tuple[float, float],
    *,
    required: bool,
) -> float | int | None:
    if not required and (key not in data or data[key] is None):
        return None
    value = _number(data, key, cast)
    low, high = bounds
    if value < low or value > high:
        raise ValueError(f"bad {key}")
    return value


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
    # 缺字段写成 NULL，更新时用 COALESCE 保留原来的电量和等级，避免半包心跳把节点抹空。
    conn.execute(
        "INSERT INTO nodes(id,type,batt,mode,level,rssi,last_seen) VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "type=COALESCE(excluded.type, nodes.type),"
        "batt=COALESCE(excluded.batt, nodes.batt),"
        "mode=COALESCE(excluded.mode, nodes.mode),"
        "level=COALESCE(excluded.level, nodes.level),"
        "rssi=COALESCE(excluded.rssi, nodes.rssi),"
        "last_seen=excluded.last_seen",
        (
            node,
            _bounded(data, "type", int, (0, 255), required=False),
            _bounded(data, "batt", float, _BATT, required=False),
            _bounded(data, "mode", int, _MODE, required=False),
            _bounded(data, "level", int, _LEVELS, required=False),
            _bounded(data, "rssi", int, _RSSI, required=False),
            now,
        ),
    )


def _alert(conn: sqlite3.Connection, node: int, data: dict[str, Any], now: float) -> None:
    level = _bounded(data, "level", int, _LEVELS, required=True)
    speed = _bounded(data, "speed", float, _SPEED, required=True)
    dist = _bounded(data, "dist", float, _DIST, required=True)
    ttc = _bounded(data, "ttc", float, _TTC, required=True)
    mode = _bounded(data, "mode", int, _MODE, required=False)
    conn.execute(
        "INSERT INTO alerts(ts,node,level,speed,dist,ttc) VALUES(?,?,?,?,?,?)",
        (now, node, level, speed, dist, ttc),
    )
    conn.execute(
        "INSERT INTO nodes(id,type,level,mode,last_seen) VALUES(?,1,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET level=excluded.level,"
        "mode=COALESCE(excluded.mode, nodes.mode),last_seen=excluded.last_seen",
        (node, level, mode, now),
    )


def _event(conn: sqlite3.Connection, node: int, data: dict[str, Any], now: float) -> None:
    conn.execute(
        "INSERT INTO events(ts,node,max_level,max_speed,min_ttc,min_dist,duration_ms) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            now,
            node,
            _bounded(data, "max_level", int, _LEVELS, required=True),
            _bounded(data, "max_speed", float, _SPEED, required=True),
            _bounded(data, "min_ttc", float, _TTC, required=True),
            _bounded(data, "min_dist", float, _DIST, required=True),
            _bounded(data, "duration_ms", int, _DURATION, required=True),
        ),
    )


def _config(conn: sqlite3.Connection, node: int, data: dict[str, Any]) -> None:
    mode = _bounded(data, "mode", int, _MODE, required=True)
    conn.execute(
        "INSERT INTO nodes(id, mode) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET mode=excluded.mode",
        (node, mode),
    )
