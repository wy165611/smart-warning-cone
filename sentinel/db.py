"""SQLite 存储。表结构与原先 server/app.py 兼容。"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any

SCHEMA = """
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
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        parent = Path(path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(path: str) -> None:
    with closing(connect(path)) as conn, conn:
        conn.executescript(SCHEMA)


def fetch_all(
    path: str,
    lock: threading.Lock,
    sql: str,
    args: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    with lock, closing(connect(path)) as conn:
        return [dict(row) for row in conn.execute(sql, args).fetchall()]
