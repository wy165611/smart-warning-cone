# -*- coding: utf-8 -*-
"""挑战杯答辩 PPT 生成脚本（v2：投影可读版）。

版式原则：每页一个核心信息；正文 ≥16 pt、标题 30 pt；少用卡片和边框，多留白；
细节放讲稿备注；图片放大、每页最多一张主图；用线条图标（icons.py）代替文字块。
全部数字来自 facts.py（仓库代码或已核对的公开资料）。没有实测或调研依据的内容一律写成
【待补充…】/【待实测】/【填】/【请核对】，在页面上以灰色虚线标签或浅灰底纹弱化显示，
生成时汇总到“答辩PPT_待补充清单.md”，答辩前由团队据实替换。
用法：python gen_ppt.py（需在本目录运行，先运行 figs.py 生成 img/ 下的图）。
"""

import re

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from facts import *  # noqa: F401,F403  共享事实与数字
from icons import icon

IMG = "img/"


def C(h):
    return RGBColor.from_string(h)


NAVY, NAVY2 = C("0B2A5B"), C("061A3A")
ORANGE, CYAN, RED, GREEN = C("F28C28"), C("18A7E0"), C("E53935"), C("2E9E5B")
INK, GREY, MUTE = C("1E293B"), C("5B6B82"), C("94A3B8")
LINE, SOFT, WHITE = C("E2E8F0"), C("F4F7FB"), C("FFFFFF")
HEX = {NAVY: "#0B2A5B", ORANGE: "#F28C28", CYAN: "#18A7E0", RED: "#E53935", GREY: "#5B6B82", GREEN: "#2E9E5B"}
FONT = "微软雅黑"
PH_RE = re.compile(r"(【[^】]*】)")
SECTIONS = ["背景问题", "方案设计", "关键技术", "验证情况", "创新计划"]

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5
ML = 0.75  # 左右页边距
CW = W - 2 * ML  # 内容宽度
TOP = 2.15  # 内容区起点
state = {"page": 0}
PLACEHOLDERS = []  # (页码, 占位文字)
TEST_PAGE = 16  # “封闭场地实测计划”所在页，第 14 页引用


# ------------------------------------------------------------------ 基础
def _ph(t):
    PLACEHOLDERS.append((state["page"], t))


def _ea(run):
    rPr = run._r.get_or_add_rPr()
    rPr.set("lang", "zh-CN")
    rPr.append(rPr.makeelement(qn("a:ea"), {"typeface": FONT}))
    return rPr


def _nostyle(shape):
    """去掉主题样式引用（effectRef 会让 LibreOffice 画出阴影）。"""
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def rect(sl, x, y, w, h, fill=None, shape=MSO_SHAPE.RECTANGLE, line=None, lw=1.0, dash=False, radius=None):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
        if dash:
            s.line.dash_style = MSO_LINE.DASH
    s.shadow.inherit = False
    _nostyle(s)
    if radius is not None:
        s.adjustments[0] = radius
    return s


def line(sl, x1, y1, x2, y2, color=LINE, w=1.0, arrow=False):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(w)
    _nostyle(c)
    if arrow:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def text(sl, x, y, w, h, t, size=18, color=INK, bold=False, align="l", anchor="t", spacing=1.15, after=0, dark=False):
    """t 可以是字符串、字符串列表（每项一段），或段内 [(文字, {size,bold,color}), …] 的列表。
    【…】占位符自动弱化为浅灰底纹 + 灰字，并记入待补充清单。"""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    paras = []
    for item in t if isinstance(t, list) else [t]:
        if isinstance(item, str):
            paras.extend([[(s, {})] for s in item.split("\n")])
        else:
            paras.append(item)
    for i, segs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        p.line_spacing = spacing
        if after:
            p.space_after = Pt(after)
        for seg0, opt in segs:
            for seg in PH_RE.split(seg0):
                if not seg:
                    continue
                r = p.add_run()
                r.text = seg
                f = r.font
                f.name = FONT
                f.size = Pt(opt.get("size", size))
                f.bold = opt.get("bold", bold)
                is_ph = seg.startswith("【") and seg.endswith("】")
                if is_ph:
                    _ph(seg)
                    f.bold = False
                    f.color.rgb = C("C3CCD9") if dark else C("7A8699")
                else:
                    f.color.rgb = opt.get("color", color)
                rPr = _ea(r)
                if is_ph:
                    hl = rPr.makeelement(qn("a:highlight"), {})
                    hl.append(hl.makeelement(qn("a:srgbClr"), {"val": "23406E" if dark else "EEF1F5"}))
                    rPr.find(qn("a:solidFill")).addnext(hl)
    return tb


def tag(sl, x, y, w, t, h=0.42, dark=False, size=13, align="l"):
    """待补充标签：灰色虚线框 + 灰字，视觉上不抢主信息。"""
    _ph(t)
    s = rect(sl, x, y, w, h, None, MSO_SHAPE.ROUNDED_RECTANGLE, line=C("8DA0BA") if dark else MUTE, lw=1.0, dash=True, radius=0.25)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.12)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER}[align]
    r = p.add_run()
    r.text = t
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.color.rgb = C("C3CCD9") if dark else C("7A8699")
    _ea(r)
    return s


def pic(sl, path, x, y, w=None, h=None, crop_to=None):
    """crop_to=(w,h) 时按比例居中裁剪后铺满；只给 w 或 h 时按原比例。"""
    if crop_to:
        cw, ch = crop_to
        iw, ih = Image.open(path).size
        target, cur = cw / ch, iw / ih
        p = sl.shapes.add_picture(path, Inches(x), Inches(y), Inches(cw), Inches(ch))
        if cur > target:
            e = (1 - target / cur) / 2
            p.crop_left = p.crop_right = e
        else:
            e = (1 - cur / target) / 2
            p.crop_top = p.crop_bottom = e
        return p
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return sl.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def fit_pic(sl, path, x, y, w, h):
    """在 (x,y,w,h) 框内按原比例放到最大并居中。"""
    iw, ih = Image.open(path).size
    s = min(w / iw, h / ih)
    pw, ph = iw * s, ih * s
    return pic(sl, path, x + (w - pw) / 2, y + (h - ph) / 2, w=pw, h=ph)


def ico(sl, name, x, y, size, color=NAVY, disc=None):
    """线条图标；disc 给出底色时画一个浅色圆底。"""
    if disc is not None:
        rect(sl, x, y, size, size, disc, MSO_SHAPE.OVAL)
        pad = size * 0.24
        pic(sl, icon(name, HEX[color]), x + pad, y + pad, w=size - 2 * pad, h=size - 2 * pad)
    else:
        pic(sl, icon(name, HEX[color]), x, y, w=size, h=size)


def tint(c, k=0.88):
    """把颜色往白色混合，得到浅色底。"""
    r, g, b = c[0], c[1], c[2]
    return RGBColor(int(r + (255 - r) * k), int(g + (255 - g) * k), int(b + (255 - b) * k))


def notes(sl, t):
    sl.notes_slide.notes_text_frame.text = t


def alpha(shape, val):
    sp = shape.fill._xPr.find(qn("a:solidFill"))[0]
    sp.append(sp.makeelement(qn("a:alpha"), {"val": str(val)}))


def ref(key):
    return f"[{ref_no(key)}]"


def source(sl, t, y=6.62, x=ML, w=CW, align="l"):
    text(sl, x, y, w, 0.3, t, size=12, color=MUTE, align=align)


# ------------------------------------------------------------------ 版式
def content_slide(sec_idx, title, msg=""):
    sl = prs.slides.add_slide(BLANK)
    state["page"] += 1
    # 章节标签 + 进度条
    text(sl, ML, 0.42, 6, 0.32, f"{sec_idx + 1:02d}   {SECTIONS[sec_idx]}", size=14, color=ORANGE, bold=True)
    for i in range(len(SECTIONS)):
        rect(sl, W - ML - (len(SECTIONS) - i) * 0.46 + 0.1, 0.55, 0.36, 0.07, ORANGE if i == sec_idx else LINE)
    text(sl, ML, 0.76, CW, 0.66, title, size=30, color=NAVY, bold=True, anchor="m")
    if msg:
        text(sl, ML, 1.46, CW, 0.42, msg, size=18, color=GREY)
    # 页脚
    line(sl, ML, 6.98, W - ML, 6.98, LINE, 0.75)
    text(sl, ML, 7.04, 8, 0.28, "哨兵 · 公路养护作业区智能预警锥桶", size=10, color=MUTE)
    text(sl, W - ML - 1, 7.04, 1, 0.28, str(state["page"]), size=10, color=MUTE, align="r")
    return sl


def stat(sl, x, y, w, num, unit, label, color=NAVY, nsize=48, align="l", lsize=16):
    text(sl, x, y, w, 0.9, [[(num, {"size": nsize, "bold": True, "color": color}), (" " + unit, {"size": 20, "bold": True, "color": color})]], align=align, anchor="b")
    text(sl, x, y + 0.95, w, 0.8, label, size=lsize, color=GREY, align=align, spacing=1.2)


def table(sl, x, y, w, rows, col_w, size=16, row_h=0.5, highlight_col=None, first_bold=True, align=None):
    shp = sl.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shp.table
    tblPr = tbl._tbl.tblPr
    for k in ("firstRow", "bandRow"):
        tblPr.set(k, "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = tblPr.makeelement(qn("a:tableStyleId"), {})
        tblPr.append(sid)
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j, v in enumerate(row):
            c = tbl.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = Inches(0.12)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]
            a = (align or ["l"] * len(row))[j]
            p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER}[a]
            r = p.add_run()
            r.text = v
            r.font.name = FONT
            r.font.size = Pt(size)
            _ea(r)
            is_ph = v.startswith("【")
            fill = None
            if i == 0:
                fill = NAVY if highlight_col is None or j != highlight_col else ORANGE
                r.font.color.rgb = WHITE
                r.font.bold = True
            elif is_ph:
                _ph(v)
                r.font.color.rgb = C("7A8699")
                fill = C("F6F8FB")
            elif highlight_col is not None and j == highlight_col:
                fill = C("FFF4EA")
                r.font.color.rgb = C("B45309")
                r.font.bold = True
            else:
                r.font.color.rgb = INK
                r.font.bold = first_bold and j == 0
            if fill is not None:
                c.fill.solid()
                c.fill.fore_color.rgb = fill
            else:
                c.fill.background()
            # 只画行底细线
            tcPr = c._tc.get_or_add_tcPr()
            for tagname in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = tcPr.makeelement(qn(tagname), {"w": "9525" if tagname == "a:lnB" else "0"})
                if tagname == "a:lnB":
                    sf = ln.makeelement(qn("a:solidFill"), {})
                    sf.append(sf.makeelement(qn("a:srgbClr"), {"val": "D5DDE8"}))
                    ln.append(sf)
                else:
                    ln.append(ln.makeelement(qn("a:noFill"), {}))
                tcPr.append(ln)
            # lnX 必须排在 fill 之前
            fills = [e for e in tcPr if e.tag in (qn("a:solidFill"), qn("a:noFill"))]
            for e in fills:
                tcPr.remove(e)
                tcPr.append(e)
    return tbl


def numbered(sl, x, y, w, items, gap=1.05, color=ORANGE, tsize=20, bsize=16):
    """序号 + 粗体短语 + 一行说明，无边框。"""
    for i, (h_, b_) in enumerate(items):
        yy = y + i * gap
        text(sl, x, yy - 0.04, 0.7, 0.6, f"{i + 1:02d}", size=24, color=color, bold=True)
        text(sl, x + 0.75, yy, w - 0.75, 0.42, h_, size=tsize, color=NAVY, bold=True)
        text(sl, x + 0.75, yy + 0.44, w - 0.75, 0.5, b_, size=bsize, color=GREY)


# ================================================================== 1 封面
sl = prs.slides.add_slide(BLANK)
state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, 8.2, H, NAVY2)
alpha(ov, 88000)
text(sl, ML, 0.8, 7.2, 0.7, [f"{COMPETITION}", f"{CATEGORY}（B 类）"], size=14, color=C("C9D8EE"), spacing=1.25)
text(sl, ML, 1.95, 7.2, 1.2, "哨  兵", size=66, color=WHITE, bold=True)
text(sl, ML, 3.2, 7.2, 1.2, SHORT_TITLE, size=26, color=WHITE, bold=True, spacing=1.2)
rect(sl, ML + 0.03, 4.55, 1.2, 0.07, ORANGE)
text(sl, ML, 4.78, 7.2, 0.5, "让锥桶测到来车，按危险程度提醒", size=20, color=ORANGE, bold=True)
text(sl, ML, 5.7, 7.2, 1.0, ["答辩人 【填】   团队成员 【填】   指导教师 【填】", f"{SCHOOL} 【请核对】"], size=15, color=WHITE, spacing=1.45, dark=True)
tag(sl, 6.85, 0.8, 1.0, "校徽", h=0.42, dark=True, size=12, align="c")
text(sl, 8.6, H - 0.45, 4.4, 0.3, "背景为 AI 生成的概念图，答辩前替换为实物照片", size=10, color=C("DDDDDD"), align="r")
notes(sl, "各位评委老师好，我们是“哨兵”团队。作品是基于毫米波雷达与协同组网的公路养护作业区智能预警锥桶系统：让锥桶能测到来车，并按危险程度提醒司机和工人。下面按背景问题、方案设计、关键技术、验证情况、创新与计划五部分汇报。【封面：答辩人、团队成员、指导教师、校徽、学校学院按实际填写和核对；背景图为 AI 生成的概念图，答辩前换成实物照片】")

# ================================================================== 2 目录
sl = prs.slides.add_slide(BLANK)
state["page"] += 1
rect(sl, 0, 0, 4.4, H, NAVY2)
text(sl, ML, 2.75, 3.4, 1.0, "目录", size=48, color=WHITE, bold=True)
text(sl, ML + 0.02, 3.75, 3.4, 0.5, "CONTENTS", size=18, color=ORANGE, bold=True)
items = [("背景问题", "作业区风险与现有设施的缺口"), ("方案设计", "四类节点 · 三层架构 · 现场布设"), ("关键技术", "TTC 分级 · 滤波防误报 · 组网"),
         ("验证情况", "已完成的软件验证 · 待做的实测"), ("创新计划", "作品特点 · 应用路径 · 团队计划")]
for i, (a_, b_) in enumerate(items):
    y = 0.95 + i * 1.18
    text(sl, 5.3, y, 1.1, 0.8, f"{i + 1:02d}", size=34, color=ORANGE, bold=True, anchor="m")
    text(sl, 6.55, y + 0.02, 5.5, 0.45, a_, size=24, color=NAVY, bold=True)
    text(sl, 6.57, y + 0.47, 6.0, 0.36, b_, size=16, color=GREY)
    if i < 4:
        line(sl, 5.3, y + 1.03, W - ML, y + 1.03, LINE, 0.75)
notes(sl, "（目录页，带过即可）")

# ================================================================== 3 背景
sl = content_slide(0, "作业区是来车风险集中的地方", "边通车边施工：工人背对来车，现场噪声大")
pic(sl, IMG + "workzone.png", ML, TOP, crop_to=(6.3, 4.1))
source(sl, "示意图（AI 生成），答辩前替换为团队实地调研照片", y=6.3)
X = 7.55
stat(sl, X, TOP - 0.05, 5.0, str(FHWA_2024_DEATHS), "人", f"2024 年美国工作区交通事故死亡\n2023 年为 {FHWA_2023_DEATHS} 人", RED, nsize=54)
stat(sl, X, TOP + 1.85, 5.0, "过半", "", "致死事故发生在夜间；追尾约占四分之一", ORANGE, nsize=48)
text(sl, X, TOP + 3.45, 5.0, 0.35, f"来源：FHWA-HOP-26-060 {ref('HOP-26-060')} · 美国数据，不代表我国", size=12, color=MUTE)
tag(sl, X, TOP + 3.85, 5.0, "【待补充：我国作业区事故统计或典型案例及出处】")
notes(sl, f"养护作业通常边通车边施工，工人面向路面、背对来车，机械噪声大。美国联邦公路局2026年的资料显示，2024年美国工作区交通事故死亡{FHWA_2024_DEATHS}人（2023年{FHWA_2023_DEATHS}人），超过一半的致死事故发生在夜间，追尾约占四分之一。这是美国数据，我们只用它说明这类风险被持续统计，不能代表我国。我国到2025年末公路里程{ROAD_KM}万公里，其中农村公路{RURAL_KM}万公里（交通运输部统计公报{ref('2025年')}），日常小修保养点多面广。【答辩前补充一条国内统计或案例，并注明出处】")

# ================================================================== 4 缺口
sl = content_slide(0, "现有设施能隔离和告知，但看不到来车", "按功能划分，不涉及具体产品的性能和价格")
pains = [("被动", "cone", "只能隔离和告知", NAVY), ("不分级", "zap", "固定频率闪烁", CYAN), ("滞后", "clock", "越界后才报警", ORANGE),
         ("盲区", "eyeoff", "工人背对来车", RED), ("无记录", "filex", "危险接近无法复盘", GREY)]
cw = CW / 5
for i, (h_, ic_, b_, c_) in enumerate(pains):
    x = ML + i * cw
    ico(sl, ic_, x + cw / 2 - 0.6, TOP + 0.1, 1.2, c_, disc=tint(c_))
    text(sl, x, TOP + 1.5, cw, 0.6, h_, size=26, color=c_, bold=True, align="c")
    text(sl, x + 0.1, TOP + 2.12, cw - 0.2, 0.75, b_, size=17, color=GREY, align="c")
rect(sl, ML, 5.45, 0.08, 1.05, ORANGE)
text(sl, ML + 0.3, 5.4, CW - 0.3, 0.5, "目标：在规范设施之外，给普通锥桶加一层主动提醒", size=22, color=NAVY, bold=True)
text(sl, ML + 0.3, 5.98, CW - 0.3, 0.45, "测到来车  →  算出还剩几秒  →  按危险程度提醒司机和工人  →  留下记录", size=18, color=GREY)
notes(sl, "按功能看，现有设施有五个缺口：锥桶、水马、标志牌是被动的，只能隔离和告知；爆闪灯固定频率闪烁，不区分车辆危险程度；入侵报警多在车辆越界或碰撞后才触发；工人背对来车、噪声大，很难察觉；危险接近发生过几次，事后没有记录、无法查证。我们的目标是在规范要求的设施之外，给普通锥桶加一层主动提醒：测到来车、算出还剩几秒、按危险程度提醒司机和工人，并留下记录。")

# ================================================================== 5 依据与定位
sl = content_slide(0, "依据与定位：补充，而不是替代", "标准规定设施怎么摆，本作品负责“看见来车”")
basis = [(f"JTG H30—2015 {ref('2015年第16号')}", "公路养护安全作业规程"),
         (f"GB 5768.4—2017 {ref('GB 5768.4')}", "道路交通标志和标线 第 4 部分：作业区"),
         (f"23 CFR 630.1108 {ref('630.1108')}", "入侵报警、速度管理、ITS 列为可选措施"),
         (f"FHWA EDC-8 {ref('EDC-8')}", "夜间作业区推广自动入侵报警、顺序警示灯")]
for i, (h_, b_) in enumerate(basis):
    y = TOP + i * 1.02
    text(sl, ML, y, 5.7, 0.42, h_, size=20, color=NAVY, bold=True)
    text(sl, ML, y + 0.44, 5.7, 0.4, b_, size=16, color=GREY)
layers = [("管理", "接近事件入库 · 安全报告 · 复盘", NAVY, "report"), ("本作品", "测距测速 → TTC 分级 → 多端提醒", ORANGE, "radar"),
          ("规范设施", "标志 · 锥桶 · 防撞设施（按规范布设）", GREY, "cone")]
X = 6.75
for i, (h_, b_, c_, ic_) in enumerate(layers):
    y = TOP + i * 1.38
    rect(sl, X, y, W - ML - X, 1.2, tint(c_, 0.9) if c_ != ORANGE else ORANGE, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    fg = WHITE if c_ == ORANGE else c_
    pic(sl, icon(ic_, "#FFFFFF" if c_ == ORANGE else HEX[c_]), X + 0.3, y + 0.3, w=0.6, h=0.6)
    text(sl, X + 1.15, y + 0.14, 3.8, 0.45, h_, size=21, color=fg, bold=True)
    text(sl, X + 1.15, y + 0.6, W - ML - X - 1.3, 0.5, b_, size=16, color=WHITE if c_ == ORANGE else INK)
text(sl, ML, 6.35, CW, 0.4, "入侵报警、顺序警示灯在国外已有应用，本作品不是首创，定位是低成本集成", size=16, color=GREY)
notes(sl, "我们的定位是补充而不是替代。作业区怎么划分、标志和锥桶怎么摆，按JTG H30—2015《公路养护安全作业规程》和GB 5768.4—2017执行；美国联邦法规23 CFR 630.1108把入侵报警、速度管理、智能交通系统列为可选措施，联邦公路局EDC-8夜间作业区专题也在推广自动入侵报警和顺序点亮的警示灯。所以这类思路不是我们首创，我们的特点是把TTC提前分级、流水灯、工人穿戴端和事件记录集成到一个低成本的锥桶节点里。右侧三层：底层是规范设施，中间是本作品的主动预警，上层是管理与复盘。")

# ================================================================== 6 方案总览
sl = content_slide(1, "方案总览：四类节点协同预警", "卡装在标准锥桶顶部，不改造现有设施")
pic(sl, IMG + "hero_cone.png", ML, TOP, crop_to=(5.6, 4.3))
source(sl, "概念渲染图（AI 生成），答辩前替换为样机照片", y=6.5)
roles = [("哨兵锥桶", "radar", "雷达测距测速，计算 TTC，三级预警", ORANGE), ("联动锥桶", "chevrons", "接收预警，错相点亮形成流水灯", CYAN),
         ("工人报警器", "vibrate", "二级预警时震动 + 蜂鸣 + 红灯", RED), ("网关与平台", "database", "MQTT 上传 · 事件入库 · 安全报告", NAVY)]
X = 6.95
for i, (h_, ic_, b_, c_) in enumerate(roles):
    y = TOP + 0.05 + i * 1.08
    ico(sl, ic_, X, y, 0.8, c_, disc=tint(c_))
    text(sl, X + 1.05, y - 0.02, 4.6, 0.45, h_, size=21, color=NAVY, bold=True)
    text(sl, X + 1.05, y + 0.42, 4.6, 0.42, b_, size=16, color=GREY)
notes(sl, "系统由四类节点组成，都卡装在标准锥桶顶部，不改造现有设施。上游的哨兵锥桶用24GHz毫米波雷达测量来车距离和速度，计算碰撞时间做三级预警；联动锥桶通过ESP-NOW接收预警，按编号错相点亮形成流水灯；工人报警器在最危险的二级预警时震动、蜂鸣并亮红灯；网关把数据转成MQTT上传，平台记录每次接近事件，提供实时看板并生成安全报告。左图是AI生成的概念渲染图，答辩前换成样机照片。")

# ================================================================== 7 架构
sl = content_slide(1, "三层架构：感知 — 边缘决策 — 平台", "判定全部在锥桶本地完成，网关或平台断开时预警照常工作")
fit_pic(sl, IMG + "arch.png", ML, TOP - 0.05, CW, 4.75)
notes(sl, f"系统分三层。感知层是24GHz雷达、ASRPRO离线语音和电量与环境模式；边缘层由哨兵完成卡尔曼滤波、TTC计算和分级判定，通过ESP-NOW广播给联动锥桶和工人端，最多{MAX_HOPS}跳；网关把报文转成MQTT上传平台，平台用FastAPI加SQLite，提供实时看板、事件库和安全报告。关键设计是判定全部在本地完成，网络中断不影响预警。")

# ================================================================== 8 布设
sl = content_slide(1, "现场布设与使用流程", "按 JTG H30 / GB 5768.4 设置作业区后，把哨兵放在上游、雷达朝来车")
fit_pic(sl, IMG + "layout.png", ML, TOP - 0.1, CW, 3.55)
steps = [("放置", "pin", "上游放置，朝向来车"), ("启动", "mic", "语音“开始作业”"), ("预警", "bell", "声光、流水灯、震动"), ("收工", "flag", "“结束作业”出报告")]
sw = CW / 4
for i, (h_, ic_, b_) in enumerate(steps):
    x = ML + i * sw
    ico(sl, ic_, x, 5.78, 0.66, ORANGE if i == 2 else NAVY, disc=tint(ORANGE if i == 2 else NAVY))
    text(sl, x + 0.8, 5.7, sw - 0.82, 0.4, h_, size=20, color=NAVY, bold=True)
    text(sl, x + 0.8, 6.12, sw - 0.82, 0.4, b_, size=16, color=GREY)
notes(sl, "现场使用分四步：先按规范设置作业区，再把哨兵放在上游，雷达朝向来车，具体距离按限速和视距确定，图中50到150米只是示意；联动锥桶沿过渡区摆放。对哨兵说“小哨兵，开始作业”启动，语音播报确认；有危险时自动声光报警、流水灯引导，并让工人报警器震动；收工说“结束作业”，平台生成安全报告。")

# ================================================================== 9 TTC
sl = content_slide(2, "TTC 与超速双判据，三级分级预警", f"TTC = 距离 ÷ 接近速度：车辆保持当前速度还需几秒到达 {ref('Hayward')}")
fit_pic(sl, IMG + "ttc_map.png", ML, TOP - 0.05, 6.4, 4.5)
lv = [("安全", f"TTC ≥ {TTC1:g} s 且未超速", "黄灯慢闪 · 工人端静默", GREEN),
      ("一级", f"TTC < {TTC1:g} s 或车速 > {SPEED_LIMIT}×{OVERSPEED} km/h", "红黄快闪 + 流水灯 · 工人端 LED", ORANGE),
      ("二级", f"TTC < {TTC2:g} s", "红色爆闪 + 蜂鸣 · 工人端震动", RED)]
X = 7.55
for i, (h_, cond, act, c_) in enumerate(lv):
    y = TOP + i * 1.22
    rect(sl, X, y + 0.05, 0.1, 0.95, c_)
    text(sl, X + 0.3, y, 1.1, 0.5, h_, size=22, color=c_, bold=True)
    text(sl, X + 1.3, y + 0.03, W - ML - X - 1.3, 0.45, cond, size=17, color=NAVY, bold=True)
    text(sl, X + 1.3, y + 0.52, W - ML - X - 1.3, 0.45, act, size=16, color=GREY)
text(sl, X, TOP + 3.75, W - ML - X, 0.75, [f"雨天 ×{RAIN}　夜间 ×{NIGHT}（可叠加 ×{RAIN * NIGHT:.2f}）", "阈值与系数均为设计初值，需实测标定"], size=16, color=GREY, spacing=1.25)
notes(sl, f"判定用TTC，也就是车辆保持当前速度还需几秒到达，这一概念来自Hayward 1972年的交通冲突研究。TTC大于等于{TTC1:g}秒且未超速为安全，黄灯慢闪；TTC小于{TTC1:g}秒或车速超过限速{SPEED_LIMIT}公里每小时的{OVERSPEED}倍触发一级，红黄快闪加流水灯，工人端LED提示；小于{TTC2:g}秒触发二级，红色爆闪加蜂鸣，工人端震动。雨天阈值乘{RAIN}，夜间乘{NIGHT}，可叠加为{RAIN * NIGHT:.2f}，定性理由是湿滑路面制动距离更长、夜间视距更短。需要说明：这些阈值和系数是设计初值，要靠封闭场地实测来标定。")

# ================================================================== 10 滤波防误报
sl = content_slide(2, "卡尔曼滤波 + 防误报措施", "仿真：55 km/h 匀速接近，距离量测噪声 σ = 2 m（理论演示，非实测）")
fit_pic(sl, IMG + "sim_curve.png", ML, TOP - 0.05, 6.75, 4.5)
numbered(sl, 7.85, TOP + 0.05, W - ML - 7.85, [
    ("一维卡尔曼滤波", f"Q = 0.5，R = 4 {ref('Kalman')}，平滑跳变"),
    (f"连续 {CONFIRM} 帧确认", "条件连续满足才升级"),
    (f"{RELEASE_S:g} s 按时解除", "雷达无帧或断线也能解除"),
    ("目标筛选", "只取接近、≥5 km/h、≤100 m")], gap=1.12)
notes(sl, f"雷达读数会跳，我们用一维卡尔曼滤波平滑，参数Q取0.5、R取4；目标需连续{CONFIRM}帧满足条件才升级；目标消失{RELEASE_S:g}秒后按时间解除，这个判断放在主循环里，雷达无帧甚至串口断开时也能按时解除；只跟踪接近、速度不低于5公里每小时、100米内的目标，多目标取TTC最小的一个。左图是仿真：55公里每小时已超过48公里每小时的超速线，第3帧即进入一级，TTC降到2.5秒以下时升级二级。这是理论演示，不是实测。")

# ================================================================== 11 组网
sl = content_slide(2, "锥桶自组网：无需路由器的协同联动", f"ESP-NOW 广播 {ref('esp_now')}：不依赖路由器和移动网络")
mets = [(str(MAX_HOPS), "跳", "最多两跳中继，扩大覆盖"), (str(REPEAT_MS), "ms", "预警期间重发间隔"), (str(LINK_TIMEOUT_S), "s", "收不到刷新即回安全"), ("32", "位", "序号，按节点去重")]
mw = CW / 4
for i, (n_, u_, l_) in enumerate(mets):
    x = ML + i * mw
    stat(sl, x, TOP - 0.15, mw, n_, u_, l_, [ORANGE, NAVY, CYAN, RED][i], nsize=44, align="c")
    if i:
        line(sl, x, TOP + 0.1, x, TOP + 1.4, LINE, 1.0)
flow_ = [("哨兵", "radar", "等级变化立即广播", ORANGE), ("联动锥桶", "cone", "去重后转发一次", CYAN), ("联动锥桶 n", "chevrons", "错相点亮流水灯", CYAN),
         ("工人端", "vibrate", "二级：震动 + 蜂鸣", RED), ("网关", "gateway", "去重后转 MQTT", NAVY)]
fw = CW / 5
for i, (h_, ic_, b_, c_) in enumerate(flow_):
    x = ML + i * fw
    ico(sl, ic_, x + fw / 2 - 0.5, 4.2, 1.0, c_, disc=tint(c_))
    text(sl, x, 5.3, fw, 0.42, h_, size=19, color=NAVY, bold=True, align="c")
    text(sl, x, 5.74, fw, 0.42, b_, size=16, color=GREY, align="c")
    if i < 4:
        line(sl, x + fw / 2 + 0.62, 4.7, x + fw * 1.5 - 0.62, 4.7, MUTE, 1.5, arrow=True)
notes(sl, f"组网用ESP-NOW广播，不需要路由器和移动网络。哨兵等级变化立即广播，预警期间每{REPEAT_MS}毫秒重发；联动锥桶按“节点号加32位序号”去重，随机退避后转发一次，最多{MAX_HOPS}跳，并按编号错相点亮形成流水灯；工人端收到二级预警时震动加蜂鸣，并且用同一套序号去重，迟到的中继副本不会把已经解除的震动重新打开。模式不是作业中时，联动锥桶和工人端都回到安全。模式配置包（开始/结束作业、封道方向）同样去重后转发一次，离哨兵较远的锥桶也能切换；心跳与事件不转发，只由网关上传。联动锥桶和工人端{LINK_TIMEOUT_S}秒收不到刷新就回到安全状态，避免一直报警。网关对所有报文去重后转MQTT上传。")

# ================================================================== 12 工人端与语音
sl = content_slide(2, "预警直达工人，语音一句话部署", "补上“工人背对来车”的感知盲区；戴手套、无网络也能操作")
ico(sl, "vibrate", ML, TOP, 0.9, RED, disc=tint(RED))
text(sl, ML + 1.15, TOP + 0.18, 4.5, 0.55, "工人报警器", size=24, color=NAVY, bold=True)
wk = [("一级预警", "LED 提示"), ("二级预警", "震动 + 蜂鸣 + 红灯"), (f"{LINK_TIMEOUT_S} s 无刷新", "自动回到安全"), ("佩戴", "夹在安全帽或反光背心上")]
for i, (a_, b_) in enumerate(wk):
    y = TOP + 1.2 + i * 0.62
    text(sl, ML, y, 1.9, 0.45, a_, size=17, color=RED if i == 1 else NAVY, bold=True)
    text(sl, ML + 1.95, y, 3.9, 0.45, b_, size=17, color=INK)
text(sl, ML, TOP + 3.85, 3.2, 0.42, f"物料估算约 {COST_WORKER} 元", size=16, color=GREY)
tag(sl, ML + 2.55, TOP + 3.84, 3.1, "【待补充：实际采购价】")
line(sl, 6.75, TOP, 6.75, 6.6, LINE, 1.0)
X = 7.2
ico(sl, "mic", X, TOP, 0.9, NAVY, disc=tint(NAVY))
text(sl, X + 1.15, TOP + 0.18, 4.6, 0.55, "离线语音“小哨兵”", size=24, color=NAVY, bold=True)
cmds = [("开始作业 / 结束作业", "启动或收工"), ("左侧封道 / 右侧封道", "流水灯方向"), ("雨天模式 开 / 关", f"阈值 ×{RAIN}"), ("夜间模式 开 / 关", f"阈值 ×{NIGHT}"),
        ("报告电量 / 设备自检", "电量与声光自检")]
for i, (a_, b_) in enumerate(cmds):
    y = TOP + 1.2 + i * 0.62
    text(sl, X, y, 3.2, 0.45, a_, size=17, color=INK, bold=True)
    text(sl, X + 3.25, y, W - ML - X - 3.25, 0.45, b_, size=17, color=GREY)
notes(sl, f"工人报警器由ESP32-C3、振动马达、蜂鸣器和指示灯组成，锂电池供电，夹在安全帽或反光背心上：一级预警亮灯提示，二级预警震动加蜂鸣加红灯，解决工人背对来车、现场噪声大的问题；{LINK_TIMEOUT_S}秒收不到哨兵刷新自动回到安全。物料估算约{COST_WORKER}元，实际采购价待补充。部署用ASRPRO离线语音识别，唤醒词是“小哨兵”，识别结果以4字节帧（9600 8N1）发给哨兵；可以开始和结束作业、切换封道方向和雨天夜间模式、播报电量是否充足和做声光自检。戴手套、无网络也能操作。")

# ================================================================== 13 硬件与成本
sl = content_slide(2, "硬件选型与物料估算", f"哨兵节点约 {COST_SENTINEL} 元，演示套装约 {COST_KIT} 元（按常见零售价估算，未含外壳与运费）")
fit_pic(sl, IMG + "hw.png", ML, TOP, 6.5, 3.4)
text(sl, ML, 5.75, 6.5, 0.8, [f"LD2451 24 GHz 雷达：标称 ≤100 m {ref('使用手册')}", "ESP32-C3：RISC-V，支持 Wi-Fi 与 ESP-NOW"], size=16, color=GREY, spacing=1.3)
X = 7.75
text(sl, X, TOP, 5, 0.45, "单节点物料估算（元）", size=20, color=NAVY, bold=True)
costs = [("哨兵锥桶", COST_SENTINEL, ORANGE), ("联动锥桶", COST_FOLLOWER, CYAN), ("工人报警器", COST_WORKER, RED), ("网关", COST_GATEWAY, NAVY)]
for i, (n_, v_, c_) in enumerate(costs):
    y = TOP + 0.75 + i * 0.78
    text(sl, X, y, 1.65, 0.5, n_, size=17, color=INK, anchor="m")
    bw = 2.75 * v_ / COST_SENTINEL
    rect(sl, X + 1.7, y + 0.08, bw, 0.36, c_)
    text(sl, X + 1.8 + bw, y, 0.9, 0.5, str(v_), size=18, color=c_, bold=True, anchor="m")
tag(sl, X, TOP + 4.0, W - ML - X, "【待补充：实际采购价与发票】")
notes(sl, f"主控用ESP32-C3（RISC-V，支持Wi-Fi与ESP-NOW）；雷达用海凌科HLK-LD2451，24GHz，手册标称最远约100米；电源是18650锂电加TP4056充电和5伏升压。按常见零售价估算，哨兵节点约{COST_SENTINEL}元，联动锥桶约{COST_FOLLOWER}元，工人报警器约{COST_WORKER}元，网关约{COST_GATEWAY}元，演示套装约{COST_KIT}元，未含外壳与运费。实际采购价以发票为准，待补充。")

# ================================================================== 14 软件验证
sl = content_slide(3, "已完成：软件链路验证", "编译与联调记录于 2026-11-01；单元测试于 2026-11-03 复跑")
done = [("固件编译通过", "code", f"四类节点 · Flash 占用 {FLASH_USE}"), ("单元测试通过", "checklist", f"Python 参考实现 {TESTS} 项测试"),
        ("端到端联调打通", "link", "模拟器 → 入库 → 看板 → 报告")]
for i, (h_, ic_, b_) in enumerate(done):
    y = TOP + 0.05 + i * 1.22
    ico(sl, ic_, ML, y, 0.85, GREEN, disc=tint(GREEN))
    text(sl, ML + 1.1, y - 0.02, 4.9, 0.45, h_, size=21, color=NAVY, bold=True)
    text(sl, ML + 1.1, y + 0.43, 4.9, 0.42, b_, size=16, color=GREY)
text(sl, ML, TOP + 3.85, 6.0, 0.42, f"尚未完成：实物样机与封闭场地实测（见第 {TEST_PAGE} 页）", size=16, color=RED, bold=True)
fit_pic(sl, IMG + "dashboard_sim.png", 7.0, TOP - 0.05, W - ML - 7.0, 4.15)
source(sl, "平台看板截图：数据来自模拟器，不是实测", y=6.2, x=7.0, w=W - ML - 7.0, align="c")
notes(sl, f"目前完成的是软件链路验证，两件事不是同一天做的。2026-11-01：四类节点固件在{CORE}下编译通过，无编译告警，Flash占用{FLASH_USE}；本机MQTT服务器加模拟器跑通了平台入库、看板和安全报告。2026-11-03：Python参考实现复跑{TESTS}项单元测试通过，包括雷达帧解析、三级判定、非作业模式、序号去重，以及固件和Python参数一致性检查。同一天改过告警状态机和去重的固件还没有重新编译，Flash占用不能当成新固件的测量值。右图看板数据来自模拟器，不是实测。实物样机和封闭场地实测还在进行，计划见第{TEST_PAGE}页。")

# ================================================================== 15 理论时间窗
sl = content_slide(3, "理论计算：雷达距离能留出多少时间", "t = 100 m ÷ 车速（按标称最远探测距离，实际距离需实测）")
fit_pic(sl, IMG + "lead_time.png", ML, TOP - 0.05, 6.9, 4.5)
X = 8.15
stat(sl, X, TOP - 0.1, 4.4, "9.0", "s", f"车速 {SPEED_LIMIT} km/h 时", NAVY, nsize=44)
stat(sl, X, TOP + 1.3, 4.4, "6.0", "s", "车速 60 km/h 时", NAVY, nsize=44)
text(sl, X, TOP + 2.85, W - ML - X, 1.4, [[("72 km/h 以上", {"bold": True, "color": ORANGE, "size": 20})], f"不足 {TTC1:g} s，但已超过 {SPEED_LIMIT}×{OVERSPEED} km/h，按超速触发一级"], size=16, color=GREY, spacing=1.2)
notes(sl, f"这是理论计算：按雷达标称最远100米，{SPEED_LIMIT}公里每小时约有9秒，60公里每小时约6秒，都大于{TTC1:g}秒的一级阈值；车速超过72公里每小时时不足{TTC1:g}秒，但这时已经超过{SPEED_LIMIT}×{OVERSPEED}公里每小时的超速线，会按超速条件提前触发一级。局限：安装高度、车型、天气都会影响实际探测距离，要实测确认；高速路段可以研究前后两个哨兵级联，作为后续工作。")

# ================================================================== 16 实测计划
sl = content_slide(3, "待完成：封闭场地实测计划", "目标值为团队自定的验收线，实测后填入右列")
assert state["page"] == TEST_PAGE, state["page"]
rows = [["指标", "目标值", "实测值"], ["测速误差", "≤ ±3 km/h", "【待实测】"], ["测距误差", "≤ ±2 m", "【待实测】"], ["最远稳定检测距离", "≥ 80 m", "【待实测】"],
        ["一级预警提前量", "≥ 4 s", "【待实测】"], ["误报率", "≤ 5%", "【待实测】"], ["漏报率", "≤ 2%", "【待实测】"], ["联动延迟", "≤ 100 ms", "【待实测】"], ["续航", "≥ 8 h", "【待实测】"]]
table(sl, ML, TOP - 0.05, 7.6, rows, [3.2, 2.2, 2.2], size=16, row_h=0.49, align=["l", "c", "c"])
X = 9.0
ico(sl, "shield", X, TOP, 0.85, ORANGE, disc=tint(ORANGE))
text(sl, X, TOP + 1.05, W - ML - X, 0.45, "安全约束", size=21, color=NAVY, bold=True)
text(sl, X, TOP + 1.6, W - ML - X, 2.4, ["封闭场地", "自行车 / 电动车 ≤30 km/h", "专人警戒", "不用车辆冲向真人"], size=17, color=GREY, spacing=1.2, after=6)
notes(sl, "这是封闭场地实测计划，目标值是团队自己定的验收线。测试方法：测速误差在10到30公里每小时五档各测5次，对比测速仪；测距误差在路面每10米做标记，对比雷达读数；最远稳定检测距离在白天、夜间、小雨各测5次；一级预警提前量用视频逐帧计时；误报率做30分钟无目标驶近观察；漏报率做20次超阈值驶近；联动延迟用慢动作视频逐帧测10次；续航满电连续运行。测试只在封闭场地用自行车或电动车，车速不超过30公里每小时，专人警戒，不用车辆冲向真人。【实测完成后把“待实测”格子替换为实测数据，口头说明测试日期、地点和次数】")

# ================================================================== 17 创新点
sl = content_slide(4, "作品特点", "不是首创某项技术，而是面向小型养护作业的低成本集成")
inn = [("按危险程度提醒", "gauge", "TTC + 超速双判据分级", ORANGE), ("流水灯引导", "chevrons", "联动锥桶错相点亮", CYAN),
       ("预警直达工人", "vibrate", "弥补背对来车的盲区", RED), ("一句话部署", "mic", "离线语音切换作业与模式", NAVY),
       ("断网可用", "wifioff", "本地判定，不依赖路由器", NAVY), ("事件可追溯", "report", "接近事件入库，出报告", CYAN)]
gw = CW / 3
for i, (h_, ic_, b_, c_) in enumerate(inn):
    x = ML + (i % 3) * gw
    y = TOP + 0.5 + (i // 3) * 2.05
    ico(sl, ic_, x, y, 1.0, c_, disc=tint(c_))
    text(sl, x + 1.25, y + 0.05, gw - 1.35, 0.45, h_, size=21, color=NAVY, bold=True)
    text(sl, x + 1.25, y + 0.53, gw - 1.35, 0.45, b_, size=16, color=GREY)
notes(sl, "总结六个特点：一是按危险程度提醒，TTC加超速双判据分级，平时慢闪、危险时才升级；二是流水灯引导，联动锥桶错相点亮指示变道方向；三是预警直达工人，二级预警送到工人身上，弥补背对来车的盲区；四是一句话部署，离线语音切换作业、封道方向和环境模式；五是断网可用，判定在锥桶本地完成，组网不依赖路由器；六是接近事件可追溯，每次危险接近入库并自动生成安全报告。我们不说首创某项技术，价值在于把这些功能集成到小型养护作业用得上的低成本锥桶里。")

# ================================================================== 18 功能定位对比
sl = content_slide(4, "功能定位对比", "按工作原理比较，不代表具体产品")
rows = [["对比项", "锥桶 / 标志", "爆闪警示灯", "入侵报警类", "哨兵（本作品）"],
        ["工作方式", "隔离、告知", "固定频率闪烁", "检测越界或碰撞", "测距测速，算 TTC"],
        ["触发时机", "—", "常亮 / 常闪", "车辆越界后", "接近途中分级"],
        ["提醒对象", "司机", "司机", "工人（视产品）", "司机 + 工人"],
        ["数据记录", "无", "无", "视产品而定", "事件入库、报告"],
        ["参考成本", "—", "【待补充】", "【待补充】", f"物料约 {COST_KIT} 元/套"]]
table(sl, ML, TOP - 0.05, CW, rows, [2.0, 2.2, 2.3, 2.5, 2.83], size=16, row_h=0.58, highlight_col=4, align=["l", "c", "c", "c", "c"])
text(sl, ML, 5.78, CW, 0.4, f"入侵报警技术评估见 Gambatese 等（2017）{ref('32574')}；本作品同样需要实测证明效果", size=16, color=GREY)
tag(sl, ML, 6.28, 6.6, "【待补充：国内在售产品的名称、参数、价格及出处】", h=0.4)
notes(sl, "按工作原理比较，不代表具体产品：锥桶和标志负责隔离告知；爆闪灯固定频率闪烁；入侵报警类多在车辆越界后触发。本作品在车辆接近途中就按TTC分级，同时提醒司机和工人，并留下记录。入侵报警技术的评估可参考Gambatese等2017年的报告，本作品同样需要实测证明效果。各类产品价格我们还在调研，没有数据之前不做价格比较。【待补充：国内在售产品的名称、参数、价格及出处】")

# ================================================================== 19 应用前景
sl = content_slide(4, "应用场景与推广路径", "适用对象：公路养护、市政养护和占道施工单位")
nums = [(ROAD_KM, "全国公路里程", NAVY), (RURAL_KM, "其中农村公路", ORANGE), (EXPRESSWAY_KM, "高速公路", CYAN)]
nw = CW / 3
for i, (n_, l_, c_) in enumerate(nums):
    stat(sl, ML + i * nw, TOP - 0.2, nw, n_, "万公里", l_, c_, nsize=40, align="c")
    if i:
        line(sl, ML + i * nw, TOP, ML + i * nw, TOP + 1.25, LINE, 1.0)
source(sl, f"数据：交通运输部《2025年交通运输行业发展统计公报》{ref('2025年')}，2025 年末", y=TOP + 1.38, align="c")
path = [("校内", "building", "样机演示 · 封闭场地实测"), ("试用", "users", "联系养护单位短期试用"), ("改进", "sliders", "按反馈标定阈值、优化续航"), ("推广", "trend", "小批量制作，形成使用指南")]
pw = CW / 4
line(sl, ML + pw / 2, 4.6, ML + pw * 3.5, 4.6, LINE, 2.0)
for i, (h_, ic_, b_) in enumerate(path):
    x = ML + i * pw
    c_ = ORANGE if i == 0 else NAVY
    ico(sl, ic_, x + pw / 2 - 0.42, 4.18, 0.84, c_, disc=tint(c_, 0.85))
    text(sl, x, 5.1, pw, 0.42, h_, size=20, color=NAVY, bold=True, align="c")
    text(sl, x + 0.1, 5.52, pw - 0.2, 0.45, b_, size=16, color=GREY, align="c")
text(sl, ML, 6.2, 7.6, 0.4, f"政策方向：交通强国建设纲要 {ref('交通强国')} · 公路数字化转型 {ref('131')} · 治本攻坚 {ref('治本攻坚')}", size=14, color=GREY)
tag(sl, 8.45, 6.18, W - ML - 8.45, "【待补充：已联系的养护单位及试用意向】", h=0.4)
notes(sl, f"到2025年末，全国公路里程{ROAD_KM}万公里，其中农村公路{RURAL_KM}万公里（县道{COUNTY_KM}、乡道{TOWNSHIP_KM}、村道{VILLAGE_KM}万公里），高速公路{EXPRESSWAY_KM}万公里，日常小修保养点多面广。适用对象是公路养护、市政养护和占道施工单位。作品方向与交通强国建设纲要、公路数字化转型意见和安全生产治本攻坚三年行动一致。推广分四步：校内样机演示与封闭场地实测、联系养护单位短期试用、按反馈标定阈值并优化外壳与续航、小批量制作并形成使用指南。【有试用意向时在此补充】")

# ================================================================== 20 不足与团队
sl = content_slide(4, "不足、下一步与团队", "坦诚说明短板，按优先级推进")
numbered(sl, ML, TOP + 0.05, 5.9, [("实测数据", "封闭场地测试，标定阈值与系数"), ("方向判别", "LD2451 接近/远离方向需实机核对"),
                                    ("通信安全", "ESP-NOW 未加密，计划加校验与配对"), ("工程化", "外壳防水、续航测试、PCB 一体化")], gap=1.08)
X = 6.9
text(sl, X, TOP, 5, 0.45, "团队分工", size=20, color=NAVY, bold=True)
rows = [["成员", "专业", "分工"], ["【填】（负责人）", "【填】", "调研、算法、申报书"], ["【填】", "【填】", "硬件、电路、固件"], ["【填】", "【填】", "组网、平台"], ["【填】", "【填】", "外壳、调研、答辩"]]
table(sl, X, TOP + 0.55, W - ML - X, rows, [2.2, 1.0, 2.483], size=16, row_h=0.5, first_bold=False)
text(sl, X, TOP + 3.4, W - ML - X, 0.95, ["指导教师：【填】", "专利 / 软著 / 获奖：【填：没有就写“暂无”】"], size=16, color=INK, spacing=1.35)
notes(sl, "作品目前还有不足：一是缺少实测数据，阈值和环境系数需要在封闭场地标定；二是LD2451雷达接近和远离方向的判别要实机核对；三是ESP-NOW广播没有加密，计划加入报文校验与配对；四是外壳防水、续航测试和PCB一体化还要做。团队分工如右表：负责人负责需求调研、预警算法和申报书，其余成员分别负责硬件电路与固件、组网与平台、外壳调研与答辩。【团队信息、指导教师和成果按实际填写】")

# ================================================================== 21-22 参考资料（两页，单栏 16 pt）
half = 8
for k, chunk in enumerate([REFS[:half], REFS[half:]]):
    sl = content_slide(4, f"参考资料（{k + 1}/2）", "均为公开资料，已逐条打开核对（2026-11-01）")
    start = 1 + k * half
    paras = [[(f"[{i}]  ", {"bold": True, "color": NAVY}), (t_, {})] for i, (t_, _) in enumerate(chunk, start=start)]
    text(sl, ML, TOP - 0.05, CW, 4.75, paras, size=16, color=INK, spacing=1.1, after=12)
    notes(sl, "参考资料链接：\n" + "\n".join(f"[{i}] {u_}" for i, (_, u_) in enumerate(chunk, start=start)))

# ================================================================== 23 结束
sl = prs.slides.add_slide(BLANK)
state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, W, H, NAVY2)
alpha(ov, 82000)
text(sl, 0, 2.3, W, 1.2, "让锥桶测到来车，让提醒早几秒", size=44, color=WHITE, bold=True, align="c")
rect(sl, W / 2 - 0.7, 3.65, 1.4, 0.07, ORANGE)
text(sl, 0, 3.95, W, 0.7, "守护养护工人平安回家", size=24, color=ORANGE, align="c", bold=True)
text(sl, 0, 5.3, W, 0.6, "恳请各位评委老师批评指正", size=20, color=WHITE, align="c")
notes(sl, "我们希望让锥桶测到来车，让提醒早几秒，守护养护工人平安回家。汇报完毕，恳请各位评委老师批评指正。")

out = "./哨兵_挑战杯答辩PPT.pptx"
prs.save(out)

# ------------------------------------------------------------------ 待补充清单
with open("答辩PPT_待补充清单.md", "w", encoding="utf-8") as f:
    f.write("# 答辩 PPT 待补充清单\n\n由 gen_ppt.py 自动生成，勿手改。页面上以灰色虚线标签或浅灰底纹显示，答辩前据实替换。\n\n")
    f.write("| 页 | 占位内容 | 处数 |\n|---|---|---|\n")
    counts = {}
    for key in PLACEHOLDERS:
        counts[key] = counts.get(key, 0) + 1
    for (p, t), n in counts.items():
        f.write(f"| {p} | {t} | {n} |\n")
print(out, state["page"], "pages,", len(PLACEHOLDERS), "placeholders")
