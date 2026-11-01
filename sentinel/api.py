"""看板 HTTP API。"""

from __future__ import annotations

import threading
import time
from contextlib import closing

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from sentinel.db import connect, fetch_all, init_db
from sentinel.report import format_report, normalize_stats
from sentinel.settings import Settings, load_settings

STATS_SQL = (
    "SELECT COUNT(*) AS total, SUM(max_level>=1) AS warn, SUM(max_level=2) AS danger, "
    "AVG(max_speed) AS avg_speed, MAX(max_speed) AS top_speed, MIN(min_ttc) AS min_ttc "
    "FROM events WHERE ts > ?"
)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    init_db(cfg.db_path)
    app = FastAPI(title="Sentinel Cone", version="0.2.0")
    app.state.settings = cfg
    app.state.db_lock = threading.Lock()
    if cfg.static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(cfg.static_dir)), name="static")

    def rows(sql: str, args: tuple[object, ...] = ()) -> list[dict[str, object]]:
        return fetch_all(cfg.db_path, app.state.db_lock, sql, args)

    def stats_since(since: float) -> dict[str, object]:
        found = rows(STATS_SQL, (since,))
        return normalize_stats(found[0] if found else {})

    @app.get("/")
    def index() -> FileResponse:
        page = cfg.static_dir / "index.html"
        return FileResponse(page)

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/nodes")
    def nodes() -> list[dict[str, object]]:
        now = time.time()
        out = rows("SELECT * FROM nodes ORDER BY id")
        for node in out:
            seen = node.get("last_seen") or 0
            node["online"] = (now - float(seen)) < cfg.online_seconds
        return out

    @app.get("/api/alerts")
    def alerts(
        minutes: int = Query(default=10, ge=1, le=24 * 60),
    ) -> list[dict[str, object]]:
        return rows(
            "SELECT * FROM alerts WHERE ts > ? ORDER BY ts",
            (time.time() - minutes * 60,),
        )

    @app.get("/api/events")
    def events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, object]]:
        return rows("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))

    @app.get("/api/stats")
    def stats(hours: int = Query(default=24, ge=1, le=24 * 365)) -> dict[str, object]:
        return stats_since(time.time() - hours * 3600)

    @app.get("/api/report", response_class=PlainTextResponse)
    def report(hours: int = Query(default=24, ge=1, le=24 * 365)) -> str:
        summary = stats_since(time.time() - hours * 3600)
        with app.state.db_lock, closing(connect(cfg.db_path)) as conn:
            danger = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM events WHERE ts > ? ORDER BY min_ttc LIMIT 5",
                    (time.time() - hours * 3600,),
                ).fetchall()
            ]
        return format_report(summary, danger, hours)

    return app
