"""运行配置。环境变量优先，缺省值与原先 server/app.py 一致。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    """定位仓库根目录，使源码运行和容器内运行都能找到 server/static。"""
    override = os.getenv("SENTINEL_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    candidate = Path(__file__).resolve().parents[1]
    if (candidate / "server" / "static").is_dir():
        return candidate
    return candidate


@dataclass(frozen=True)
class Settings:
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    db_path: str = "cone.db"
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    static_dir: Path = Path("server/static")
    online_seconds: float = 15.0


def load_settings() -> Settings:
    root = repo_root()
    static_default = root / "server" / "static"
    static = Path(os.getenv("STATIC_DIR", str(static_default)))
    return Settings(
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        db_path=os.getenv("DB_PATH", "cone.db"),
        http_host=os.getenv("HTTP_HOST", "0.0.0.0"),
        http_port=int(os.getenv("HTTP_PORT", "8000")),
        static_dir=static,
        online_seconds=float(os.getenv("ONLINE_SECONDS", "15")),
    )
