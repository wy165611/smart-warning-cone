import json
import time

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
