import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from sentinel.api import create_app
from sentinel.db import connect
from sentinel.ingest import ingest
from sentinel.settings import Settings


def _client(tmp_path):
    app = create_app(Settings(db_path=str(tmp_path / "cone.db"), static_dir=tmp_path))
    return TestClient(app), app


def test_bad_payload_does_not_insert(tmp_path) -> None:
    _client_obj, app = _client(tmp_path)
    with connect(app.state.settings.db_path) as conn:
        assert ingest(conn, "cone/1/alert", b"not-json", time.time()) == "bad json"
        assert ingest(conn, "cone/1/alert", json.dumps({"level": 1}), time.time())
        assert ingest(conn, "cone/nope/alert", b"{}", time.time()) == "bad node"
        assert ingest(conn, "other/1/alert", b"{}", time.time()) == "bad topic"
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0


def test_api_round_trip_and_empty_report(tmp_path) -> None:
    client, app = _client(tmp_path)
    assert client.get("/api/health").json() == {"ok": True}
    assert client.get("/api/nodes").json() == []
    empty = client.get("/api/stats").json()
    assert empty["total"] == 0
    assert empty["avg_speed"] is None
    assert "没有记录到车辆通过事件" in client.get("/api/report").text
    assert client.get("/api/alerts?minutes=0").status_code == 422

    now = time.time()
    with app.state.db_lock, connect(app.state.settings.db_path) as conn:
        assert (
            ingest(
                conn,
                "cone/1/heartbeat",
                json.dumps({"type": 1, "batt": 3.91, "mode": 1, "level": 0, "rssi": -55}),
                now,
            )
            is None
        )
        assert (
            ingest(
                conn,
                "cone/1/alert",
                json.dumps({"level": 2, "mode": 1, "speed": 62.4, "dist": 28.0, "ttc": 1.62}),
                now,
            )
            is None
        )
        assert (
            ingest(
                conn,
                "cone/1/event",
                json.dumps(
                    {
                        "max_level": 2,
                        "max_speed": 62.4,
                        "min_ttc": 1.62,
                        "min_dist": 18.0,
                        "duration_ms": 4200,
                    }
                ),
                now,
            )
            is None
        )
        assert ingest(conn, "cone/2/config", json.dumps({"mode": 5}), now) is None

    nodes = client.get("/api/nodes").json()
    by_id = {node["id"]: node for node in nodes}
    assert by_id[1]["online"] is True
    assert by_id[1]["batt"] == 3.91
    assert by_id[1]["level"] == 2
    assert by_id[2]["mode"] == 5
    assert by_id[2]["online"] is False

    stats = client.get("/api/stats").json()
    assert stats["total"] == 1
    assert stats["danger"] == 1
    assert stats["top_speed"] == 62.4
    report = client.get("/api/report").text
    assert "二级预警：1 次" in report
    assert "62 km/h" in report

    alerts = client.get("/api/alerts").json()
    assert alerts[0]["ttc"] == 1.62
    assert len(client.get("/api/events?limit=10").json()) == 1


def test_bad_numbers_are_dropped_and_partial_heartbeat_keeps_battery(tmp_path) -> None:
    client, app = _client(tmp_path)
    now = time.time()
    with app.state.db_lock, connect(app.state.settings.db_path) as conn:
        assert (
            ingest(
                conn,
                "cone/1/heartbeat",
                json.dumps({"type": 1, "batt": 3.91, "mode": 1, "level": 2, "rssi": -55}),
                now,
            )
            is None
        )
        assert ingest(conn, "cone/1/heartbeat", b"{}", now + 1) is None
        huge = b'{"level":2,"mode":1,"speed":1e309,"dist":10,"ttc":1}'
        assert ingest(conn, "cone/1/alert", huge, now) is not None
        assert (
            ingest(
                conn,
                "cone/1/alert",
                json.dumps({"level": True, "speed": 10, "dist": 10, "ttc": 1}),
                now,
            )
            is not None
        )
        assert (
            ingest(
                conn,
                "cone/1/alert",
                json.dumps({"level": 9, "speed": 10, "dist": 10, "ttc": 1}),
                now,
            )
            is not None
        )
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0
    node = client.get("/api/nodes").json()[0]
    assert node["batt"] == 3.91
    assert node["level"] == 2
    assert node["rssi"] == -55


def test_dashboard_ships_chart_locally(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        Settings(db_path=str(tmp_path / "cone.db"), static_dir=root / "server" / "static")
    )
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "cdn.jsdelivr.net" not in page.text
    assert "/static/chart.umd.min.js" in page.text
    assert "alerts.length < 2 ? 5 : 0" in page.text
    script = client.get("/static/chart.umd.min.js")
    assert script.status_code == 200
    assert "Chart.js v4.4.6" in script.text[:300]
