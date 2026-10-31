import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Wedge, FancyArrowPatch, Circle, Rectangle
import numpy as np
import random

plt.rcParams["font.family"] = "Noto Sans CJK SC"
plt.rcParams["axes.unicode_minus"] = False
NAVY = "#0B2A5B"; CYAN = "#18A7E0"; ORANGE = "#F28C28"; RED = "#E53935"; GREEN = "#2E9E5B"; GREY = "#6B7A90"; YEL = "#F6C343"
OUT = "img/"


def box(ax, x, y, w, h, text, fc, tc="white", fs=12, bold=True, ec=None):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec or fc, lw=1.5)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.4)


def arrow(ax, x1, y1, x2, y2, text="", color=NAVY, fs=10, both=False, off=(0, 0.12)):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<|-|>" if both else "-|>", mutation_scale=16, color=color, lw=1.8)
    ax.add_patch(a)
    if text:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text, ha="center", va="bottom", fontsize=fs, color=color)


# 1 系统架构 ---------------------------------------------------------------
def arch():
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=200)
    ax.set_xlim(0, 13); ax.set_ylim(0, 6.2); ax.axis("off")
    ax.text(0.2, 5.85, "感知层", fontsize=13, color=GREY, fontweight="bold")
    ax.text(4.55, 5.85, "边缘决策与组网层", fontsize=13, color=GREY, fontweight="bold")
    ax.text(10.0, 5.85, "平台层", fontsize=13, color=GREY, fontweight="bold")
    box(ax, 0.2, 3.9, 3.3, 1.5, "24GHz 毫米波雷达\nHLK-LD2451\n距离 / 速度 / 角度", NAVY, fs=12)
    box(ax, 0.2, 2.0, 3.3, 1.4, "ASRPRO 离线语音\n部署 / 模式切换", CYAN, fs=12)
    box(ax, 0.2, 0.3, 3.3, 1.3, "电量与环境模式\n雨天 / 夜间", GREY, fs=12)
    box(ax, 4.5, 3.5, 3.6, 2.0, "哨兵锥桶 ESP32-C3\n卡尔曼滤波 → TTC 计算\n三级预警判定\n声光报警", ORANGE, fs=12)
    box(ax, 4.5, 1.6, 1.7, 1.3, "联动锥桶\n流水灯引导", ORANGE, fs=11)
    box(ax, 6.4, 1.6, 1.7, 1.3, "工人报警器\n震动+蜂鸣", RED, fs=11)
    box(ax, 4.5, 0.2, 3.6, 1.0, "网关：ESP-NOW → Wi-Fi/MQTT", NAVY, fs=11)
    box(ax, 9.3, 3.3, 3.5, 2.2, "安全管理平台\nFastAPI + SQLite\n实时看板 / 事件库\n安全报告", NAVY, fs=12)
    box(ax, 9.3, 0.8, 3.5, 1.8, "养护单位 / 交管\n风险量化 · 安全台账", CYAN, fs=12)
    arrow(ax, 3.5, 4.65, 4.5, 4.65, "UART 10Hz")
    arrow(ax, 3.5, 2.7, 4.5, 3.8, "")
    ax.text(3.55, 2.45, "UART", fontsize=10, color=NAVY)
    arrow(ax, 3.5, 0.95, 4.5, 3.55)
    arrow(ax, 5.35, 3.5, 5.35, 2.9, "", color=ORANGE)
    arrow(ax, 7.25, 3.5, 7.25, 2.9, "", color=RED)
    ax.text(6.3, 3.12, "ESP-NOW 广播 ≤2跳", fontsize=10, color=NAVY, ha="center")
    arrow(ax, 6.3, 1.6, 6.3, 1.2, "", color=NAVY)
    arrow(ax, 8.1, 0.7, 9.3, 3.6, "")
    ax.text(8.45, 2.1, "MQTT", fontsize=10, color=NAVY, rotation=63)
    arrow(ax, 11.05, 3.3, 11.05, 2.6)
    fig.savefig(OUT + "arch.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


# 2 作业区布设俯视图 --------------------------------------------------------
def layout():
    fig, ax = plt.subplots(figsize=(13, 4.6), dpi=200)
    ax.set_xlim(-5, 205); ax.set_ylim(-1, 11); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 200, 7.5, fc="#3C4452"))
    ax.plot([0, 200], [3.75, 3.75], color="white", lw=2, ls=(0, (6, 6)))
    ax.plot([0, 200], [0.15, 0.15], color="white", lw=1.5); ax.plot([0, 200], [7.35, 7.35], color="white", lw=1.5)
    # work area (right part, upper lane)
    ax.add_patch(Rectangle((150, 3.9), 45, 3.3, fc=YEL, alpha=0.35))
    ax.text(172, 5.5, "作业区", ha="center", va="center", fontsize=13, color="white", fontweight="bold")
    # taper cones
    xs = np.linspace(110, 150, 6); ys = np.linspace(7.0, 4.1, 6)
    for i, (x, y) in enumerate(zip(xs, ys)):
        ax.add_patch(Polygon([[x - 1.3, y - 0.45], [x + 1.3, y - 0.45], [x, y + 0.6]], fc=ORANGE, ec="white", lw=0.8))
    for x in np.arange(155, 196, 8):
        ax.add_patch(Polygon([[x - 1.3, 3.65], [x + 1.3, 3.65], [x, 4.7]], fc=ORANGE, ec="white", lw=0.8))
    # sentinel cone
    sx = 60
    ax.add_patch(Polygon([[sx - 2, 6.4], [sx + 2, 6.4], [sx, 7.9]], fc=RED, ec="white", lw=1.2))
    ax.add_patch(Polygon([[sx, 6.7], [2, 7.35], [2, 1.2]], fc=CYAN, alpha=0.30))
    ax.text(sx, 8.5, "哨兵锥桶（雷达朝来车方向）", ha="center", fontsize=11, color=NAVY, fontweight="bold")
    ax.text(32, 4.6, "雷达探测区 ≤100 m", ha="center", fontsize=10, color="white")
    # car
    ax.add_patch(FancyBboxPatch((8, 4.8), 9, 1.8, boxstyle="round,pad=0.1", fc="#DDE6F2", ec="white"))
    ax.annotate("", xy=(30, 5.7), xytext=(18, 5.7), arrowprops=dict(arrowstyle="-|>", color="white", lw=2))
    ax.text(12.5, 7.9, "来车", ha="center", fontsize=11, color=NAVY)
    # workers
    for wx in (160, 188):
        ax.plot([wx], [4.7], "o", ms=13, color=RED, mec="white", mew=1.5)
    ax.text(173.5, 8.5, "工人佩戴报警器", ha="center", fontsize=11, color=RED, fontweight="bold")
    ax.text(130, 8.5, "联动锥桶 · 流水灯引导变道", ha="center", fontsize=11, color=ORANGE, fontweight="bold")
    ax.text(198, 9.6, "网关", ha="right", fontsize=11, color=NAVY, fontweight="bold")
    ax.add_patch(Rectangle((195, 8.3), 3, 1.0, fc=NAVY))
    # distances
    ax.annotate("", xy=(60, -0.6), xytext=(150, -0.6), arrowprops=dict(arrowstyle="<->", color=NAVY))
    ax.text(105, -1.0, "上游 50–150 m（按限速与视距设置）", ha="center", va="top", fontsize=10, color=NAVY)
    fig.savefig(OUT + "layout.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


# 3 TTC 分级区域图 ----------------------------------------------------------
def ttc_map():
    fig, ax = plt.subplots(figsize=(8, 5.2), dpi=200)
    v = np.linspace(5, 80, 300)  # km/h
    d1 = v / 3.6 * 2.5; d2 = v / 3.6 * 5.0
    ax.fill_between(v, 0, d1, color=RED, alpha=0.35, label="二级预警 TTC<2.5 s")
    ax.fill_between(v, d1, d2, color=ORANGE, alpha=0.35, label="一级预警 2.5≤TTC<5 s")
    ax.fill_between(v, d2, 100, color=GREEN, alpha=0.18, label="安全 TTC≥5 s")
    ax.axvspan(48, 80, color=YEL, alpha=0.18, label="超限速20%（限速40 km/h）→至少一级")
    ax.plot(v, d1, color=RED, lw=2); ax.plot(v, d2, color=ORANGE, lw=2)
    ax.plot(v, d2 * 1.4, color=NAVY, lw=1.5, ls="--", label="雨天一级阈值（×1.4）")
    ax.set_xlim(5, 80); ax.set_ylim(0, 100)
    ax.set_xlabel("来车接近速度 (km/h)", fontsize=12); ax.set_ylabel("来车与哨兵距离 (m)", fontsize=12)
    ax.set_title("基于碰撞时间 TTC 的三级预警判定区域", fontsize=13, color=NAVY, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9); ax.grid(alpha=0.3)
    fig.savefig(OUT + "ttc_map.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


# 4 预警提前量 vs 车速 -------------------------------------------------------
def lead_time():
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=200)
    v = np.array([20, 30, 40, 50, 60, 70, 80])
    t_detect = 100 / (v / 3.6)
    react = 1.5  # s 典型驾驶员反应时间取值（设计假设）
    ax.bar(v - 2, t_detect, width=4, color=NAVY, label="雷达最远 100 m 可提供的时间")
    ax.bar(v + 2, np.full_like(v, 5.0, dtype=float), width=4, color=ORANGE, label="一级预警触发 TTC=5 s")
    for x, t in zip(v, t_detect):
        ax.text(x - 2, t + 0.3, f"{t:.1f}", ha="center", fontsize=9, color=NAVY)
    ax.axhline(2.5, color=RED, ls="--", lw=1.5, label="二级预警 TTC=2.5 s")
    ax.set_xlabel("来车速度 (km/h)", fontsize=12); ax.set_ylabel("时间 (s)", fontsize=12)
    ax.set_title("雷达探测距离可覆盖的预警时间（理论计算）", fontsize=13, color=NAVY, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3); ax.set_xticks(v)
    fig.savefig(OUT + "lead_time.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


# 5 仿真：一次接近过程 ------------------------------------------------------
def sim_curve():
    random.seed(7); np.random.seed(7)
    dt = 0.1; d = 100.0; v = 55.0
    T, D, Draw, V, TTC, L = [], [], [], [], [], []
    # 1D kalman
    xd, pd = d, 4.0
    t = 0.0; cnt = 0; level = 0
    while d > 8:
        d -= v / 3.6 * dt
        meas = d + np.random.normal(0, 2.0)
        pd += 0.5; k = pd / (pd + 4.0); xd = xd + k * (meas - xd); pd *= (1 - k)
        ttc = xd / (v / 3.6)
        want = 2 if ttc < 2.5 else (1 if (ttc < 5 or v > 48) else 0)
        cnt = cnt + 1 if want > 0 else 0
        if want > level and cnt >= 3: level = want
        if want < level: level = want
        T.append(t); D.append(xd); Draw.append(meas); V.append(v); TTC.append(min(ttc, 12)); L.append(level)
        t += dt
    T = np.array(T)
    fig, axs = plt.subplots(2, 1, figsize=(9, 6), dpi=200, sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
    axs[0].plot(T, Draw, ".", ms=2.5, color=GREY, label="雷达原始距离（加噪声 σ=2 m）")
    axs[0].plot(T, D, color=NAVY, lw=2, label="卡尔曼滤波后距离")
    ax2 = axs[0].twinx(); ax2.plot(T, TTC, color=ORANGE, lw=2, label="TTC"); ax2.set_ylabel("TTC (s)", color=ORANGE)
    ax2.axhline(5, color=ORANGE, ls=":", lw=1); ax2.axhline(2.5, color=RED, ls=":", lw=1)
    axs[0].set_ylabel("距离 (m)"); axs[0].legend(loc="upper right", fontsize=9)
    axs[0].set_title("仿真：55 km/h 车辆驶向作业区的预警过程", fontsize=13, color=NAVY, fontweight="bold")
    cols = {0: GREEN, 1: ORANGE, 2: RED}
    axs[1].step(T, L, where="post", color=NAVY, lw=2)
    for i in range(len(T) - 1):
        axs[1].axvspan(T[i], T[i + 1], color=cols[L[i]], alpha=0.25, lw=0)
    axs[1].set_yticks([0, 1, 2]); axs[1].set_yticklabels(["安全", "一级", "二级"])
    axs[1].set_xlabel("时间 (s)"); axs[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT + "sim_curve.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
    lv = np.array(L)
    first1 = T[np.argmax(lv >= 1)]; first2 = T[np.argmax(lv >= 2)]
    return dict(total=T[-1], warn_at=first1, danger_at=first2, warn_lead=T[-1] - first1)


# 6 算法流程图 --------------------------------------------------------------
def flow():
    fig, ax = plt.subplots(figsize=(13, 3.6), dpi=200)
    ax.set_xlim(0, 13); ax.set_ylim(0, 3.6); ax.axis("off")
    steps = [("雷达帧解析\n协议 V1.03", NAVY), ("目标筛选\n只取接近·限距离", NAVY),
             ("卡尔曼滤波\n距离/速度平滑", CYAN), ("TTC=距离÷速度\n选最危险目标", CYAN),
             ("环境系数\n雨×1.4 夜×1.2", GREY), ("连续3帧确认\n升级 / 1.5 s 保持", ORANGE), ("声光+广播\n工人震动·上云", RED)]
    w = 1.62; gap = 0.2
    for i, (s, c) in enumerate(steps):
        x = 0.1 + i * (w + gap)
        box(ax, x, 1.1, w, 1.5, s, c, fs=10.5)
        if i < len(steps) - 1:
            arrow(ax, x + w, 1.85, x + w + gap, 1.85)
    ax.text(6.5, 0.4, "每 100 ms 一轮（雷达有目标时输出频率），全部在锥桶本地完成，不依赖网络", ha="center", fontsize=11, color=NAVY)
    fig.savefig(OUT + "flow.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


# 7 硬件框图 ----------------------------------------------------------------
def hw():
    fig, ax = plt.subplots(figsize=(11, 5.4), dpi=200)
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.4); ax.axis("off")
    box(ax, 4.0, 1.8, 3.0, 1.9, "ESP32-C3\nRISC-V 160 MHz\nWi-Fi / ESP-NOW", NAVY, fs=12)
    box(ax, 0.2, 3.9, 3.0, 1.2, "LD2451 雷达\n5V · UART1 115200", CYAN, fs=11)
    box(ax, 0.2, 2.1, 3.0, 1.2, "ASRPRO 语音\nUART0 9600", CYAN, fs=11)
    box(ax, 0.2, 0.3, 3.0, 1.2, "电池电压采样\nADC 分压", GREY, fs=11)
    box(ax, 7.8, 3.9, 3.0, 1.2, "WS2812B 灯环\n红/黄 分级闪烁", ORANGE, fs=11)
    box(ax, 7.8, 2.1, 3.0, 1.2, "有源蜂鸣器\nAO3400 MOSFET 驱动", RED, fs=11)
    box(ax, 7.8, 0.3, 3.0, 1.2, "18650 + TP4056\n+ 5V 升压", GREY, fs=11)
    arrow(ax, 3.2, 4.5, 4.0, 3.4, both=True); arrow(ax, 3.2, 2.7, 4.0, 2.7, both=True); arrow(ax, 3.2, 0.9, 4.0, 2.0)
    arrow(ax, 7.0, 3.4, 7.8, 4.5); arrow(ax, 7.0, 2.7, 7.8, 2.7); arrow(ax, 7.8, 0.9, 7.0, 2.0)
    fig.savefig(OUT + "hw.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


if __name__ == "__main__":
    arch(); layout(); ttc_map(); lead_time(); flow(); hw()
    print(sim_curve())
