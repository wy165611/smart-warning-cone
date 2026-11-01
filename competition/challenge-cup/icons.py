"""答辩 PPT 用的线条图标（手写 SVG，24×24 网格），用 CairoSVG 渲染成 PNG。

用法：from icons import icon；icon("radar", "#F28C28") 返回 PNG 路径（img/icons/ 下，按需生成）。
"""
import os

import cairosvg

PATHS = {
    # 雷达：中心点 + 两道扫描弧 + 扫描线
    "radar": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="5.5"/><circle cx="12" cy="12" r="1.2"/>'
    '<path d="M12 12l6.5-6.5"/>',
    "cone": '<path d="M10 3h4l4.5 16h-13z"/><path d="M8.6 9h6.8"/><path d="M7.4 14h9.2"/><path d="M3 19h18v2H3z"/>',
    "worker": '<path d="M7 9a5 5 0 0 1 10 0"/><path d="M5.5 9h13"/><circle cx="12" cy="12.5" r="2.5"/>'
    '<path d="M5 22v-1.5A4.5 4.5 0 0 1 9.5 16h5a4.5 4.5 0 0 1 4.5 4.5V22"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "broadcast": '<path d="M4.9 19.1a10 10 0 0 1 0-14.2"/><path d="M7.8 16.2a6 6 0 0 1 0-8.4"/><circle cx="12" cy="12" r="2"/>'
    '<path d="M16.2 7.8a6 6 0 0 1 0 8.4"/><path d="M19.1 4.9a10 10 0 0 1 0 14.2"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14a8 3 0 0 0 16 0V5"/><path d="M4 12a8 3 0 0 0 16 0"/>',
    "mic": '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "eyeoff": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/><path d="M3 3l18 18"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "zap": '<path d="M13 2L3 14h9l-1 8 10-12h-9z"/>',
    "filex": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'
    '<path d="M9.5 12.5l5 5"/><path d="M14.5 12.5l-5 5"/>',
    "report": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'
    '<path d="M8 13h8"/><path d="M8 17h8"/><path d="M8 9h2"/>',
    "chevrons": '<path d="M4 6l6 6-6 6"/><path d="M11 6l6 6-6 6"/><path d="M18 6v12"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/>'
    '<path d="M9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="M7.5 12.5l3 3 6-7"/>',
    "gauge": '<path d="M3.3 19a10 10 0 1 1 17.4 0"/><path d="M12 14l4.5-4.5"/><circle cx="12" cy="14" r="1.5"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "power": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
    "flag": '<path d="M5 22V3"/><path d="M5 4h13l-2.5 4.5L18 13H5"/>',
    "code": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M7 10l3 2.5L7 15"/><path d="M12.5 15H17"/>',
    "checklist": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
    '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "building": '<path d="M3 21h18"/><path d="M5 21V8l7-5 7 5v13"/><path d="M9.5 21v-5h5v5"/><path d="M9.5 11h5"/>',
    "users": '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/>'
    '<path d="M16 3.1a4 4 0 0 1 0 7.8"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/>',
    "trend": '<path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "vibrate": '<rect x="8" y="3" width="8" height="18" rx="1.5"/><path d="M4 8v8"/><path d="M20 8v8"/><path d="M1.5 10v4"/>'
    '<path d="M22.5 10v4"/>',
    "gateway": '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 16.5h.01M11 16.5h.01"/>'
    '<path d="M8.5 9.5a5 5 0 0 1 7 0"/><path d="M5.5 6.5a9.5 9.5 0 0 1 13 0"/>',
    "wifioff": '<path d="M2 2l20 20"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M5 12.9a10 10 0 0 1 5.2-2.8"/>'
    '<path d="M19 12.9a10 10 0 0 0-2.7-1.9"/><path d="M2 8.8a15 15 0 0 1 4.2-2.7"/><path d="M10.7 5a15 15 0 0 1 11.3 3.8"/>'
    '<path d="M12 20h.01"/>',
    "battery": '<rect x="2" y="7" width="16" height="10" rx="2"/><path d="M22 11v2"/><path d="M6 10v4M10 10v4"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "box": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5"/><path d="M12 13v8"/>',
    "compass": '<circle cx="12" cy="12" r="10"/><path d="M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z"/>',
}

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "icons")


def icon(name: str, color: str = "#0B2A5B", size: int = 256, stroke: float = 1.8) -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}_{color.lstrip('#')}.png")
    if not os.path.exists(path):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
        )
        cairosvg.svg2png(bytestring=svg.encode(), write_to=path, output_width=size, output_height=size)
    return path


if __name__ == "__main__":
    for n in PATHS:
        icon(n)
    print(len(PATHS), "icons ->", OUT)
