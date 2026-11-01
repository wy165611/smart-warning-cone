"""作业区安全报告文本。没有事件时不把空统计打印成 0 秒 TTC。"""

from __future__ import annotations

import math
import time
from typing import Any


def format_fixed(value: float, digits: int) -> str:
    """非负数下与看板 Number.toFixed 一致（.5 进位，不走 Python 的银行家舍入）。"""
    factor = 10**digits
    scaled = math.floor(float(value) * factor + 0.5)
    return f"{scaled / factor:.{digits}f}"


def format_kmh(value: float) -> str:
    return format_fixed(value, 0)


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
        f"平均最高车速：{format_fixed(stats['avg_speed'], 1)} km/h；"
        f"最高车速：{format_fixed(stats['top_speed'], 1)} km/h；"
        f"最小 TTC：{format_fixed(stats['min_ttc'], 2)} s"
    )
    lines.append(f"最危险的 {len(events)} 次接近（按最小 TTC 排序，最多列 5 次）：")
    for event in events:
        clock = time.strftime("%H:%M:%S", time.localtime(event["ts"]))
        lines.append(
            f"  {clock}  车速 {format_kmh(event['max_speed'])} km/h  "
            f"最小TTC {format_fixed(event['min_ttc'], 2)}s  "
            f"最近 {format_fixed(event['min_dist'], 0)} m"
        )
    return "\n".join(lines)
