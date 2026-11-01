"""作业区安全报告文本。没有事件时不把空统计打印成 0 秒 TTC。"""

from __future__ import annotations

import math
import time
from typing import Any


def format_kmh(value: float) -> str:
    """与看板 toFixed(0) 一样，四舍五入到整数。"""
    return str(math.floor(float(value) + 0.5))


def normalize_stats(row: dict[str, Any]) -> dict[str, Any]:
    total = int(row.get("total") or 0)
    if total == 0:
        return {
            "total": 0,
            "warn": 0,
            "danger": 0,
            "avg_speed": None,
            "top_speed": None,
            "min_ttc": None,
        }
    return {
        "total": total,
        "warn": int(row.get("warn") or 0),
        "danger": int(row.get("danger") or 0),
        "avg_speed": row.get("avg_speed"),
        "top_speed": row.get("top_speed"),
        "min_ttc": row.get("min_ttc"),
    }


def format_report(stats: dict[str, Any], events: list[dict[str, Any]], hours: int) -> str:
    lines = [f"作业区安全报告（最近 {hours} 小时）"]
    if not stats["total"]:
        lines.append("该时段没有记录到车辆通过事件。")
        return "\n".join(lines)
    lines.append(
        f"通过车辆事件：{stats['total']} 次；一级以上预警：{stats['warn']} 次；"
        f"二级预警：{stats['danger']} 次"
    )
    lines.append(
        f"平均最高车速：{stats['avg_speed']:.1f} km/h；"
        f"最高车速：{stats['top_speed']:.1f} km/h；"
        f"最小 TTC：{stats['min_ttc']:.2f} s"
    )
    lines.append("最危险的 5 次接近：")
    for event in events:
        clock = time.strftime("%H:%M:%S", time.localtime(event["ts"]))
        lines.append(
            f"  {clock}  车速 {format_kmh(event['max_speed'])} km/h  "
            f"最小TTC {event['min_ttc']:.2f}s  最近 {event['min_dist']:.0f} m"
        )
    return "\n".join(lines)
