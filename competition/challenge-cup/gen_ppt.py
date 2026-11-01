# -*- coding: utf-8 -*-
"""挑战杯答辩 PPT 生成脚本。

风格：科技蓝 + 顶部导航条 + 卡片。全部数字来自 facts.py（仓库代码或已核对的公开资料）；
没有实测或调研依据的内容一律写成【待补充…】/【填…】并以黄色标出，答辩前由团队据实替换。
用法：python gen_ppt.py（需在本目录运行，先运行 figs.py 生成 img/ 下的图）。
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from PIL import Image

from facts import *  # noqa: F401,F403  共享事实与数字

IMG = "img/"
NAVY = RGBColor(0x0B, 0x2A, 0x5B); NAVY2 = RGBColor(0x06, 0x1A, 0x3A)
CYAN = RGBColor(0x18, 0xA7, 0xE0); ORANGE = RGBColor(0xF2, 0x8C, 0x28); RED = RGBColor(0xE5, 0x39, 0x35)
WHITE = RGBColor(255, 255, 255); BG = RGBColor(0xF4, 0xF7, 0xFB); GREY = RGBColor(0x5B, 0x6B, 0x82)
LIGHT = RGBColor(0xE3, 0xEC, 0xF7); INK = RGBColor(0x1E, 0x29, 0x3B); YEL = RGBColor(0xFF, 0xF2, 0x9E)
FONT = "微软雅黑"
PH_INK = RGBColor(0x8A, 0x4B, 0x00)
PH_SPLIT = __import__("re").compile(r"(【[^】]*】)")
SECTIONS = ["背景问题", "方案设计", "关键技术", "验证情况", "创新计划"]

prs = Presentation()
prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5
state = {"page": 0}


# ------------------------------------------------------------------ 基础
def rect(sl, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, line=None, radius=None):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line; s.line.width = Pt(1.25)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def text(sl, x, y, w, h, t, size=16, color=INK, bold=False, align="l", anchor="t", spacing=1.15, font=FONT):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    lines = t if isinstance(t, list) else [t]
    flat = []
    for line in lines:
        if isinstance(line, str):
            flat.extend(line.split("\n"))
        else:
            flat.append(line)
    lines = flat
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        p.line_spacing = spacing
        segs = line if isinstance(line, list) else [(line, {})]
        for seg0, opt in segs:
            for seg in PH_SPLIT.split(seg0):
                if not seg:
                    continue
                r = p.add_run(); r.text = seg
                f = r.font; f.name = FONT; f.size = Pt(opt.get("size", size)); f.bold = opt.get("bold", bold)
                is_ph = seg.startswith("【") and seg.endswith("】")
                f.color.rgb = PH_INK if is_ph and color != WHITE else opt.get("color", color)
                rPr = r._r.get_or_add_rPr()
                rPr.set("lang", "zh-CN")
                if is_ph:
                    hl = rPr.makeelement(qn("a:highlight"), {})
                    hl.append(hl.makeelement(qn("a:srgbClr"), {"val": "FFF29E" if color != WHITE else "8A6D00"}))
                    rPr.find(qn("a:solidFill")).addnext(hl)
                ea = rPr.makeelement(qn("a:ea"), {"typeface": FONT}); rPr.append(ea)
    return tb


def shape_text(s, t, size=16, color=WHITE, bold=True, align="c"):
    tf = s.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = t if isinstance(t, list) else [t]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER}[align]
        r = p.add_run(); r.text = line
        r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
        rPr = r._r.get_or_add_rPr(); ea = rPr.makeelement(qn("a:ea"), {"typeface": FONT}); rPr.append(ea)


def pic(sl, path, x, y, w=None, h=None, crop_to=None):
    """crop_to=(w,h) 时按比例居中裁剪后铺满"""
    if crop_to:
        cw, ch = crop_to
        im = Image.open(path); iw, ih = im.size
        target = cw / ch; cur = iw / ih
        p = sl.shapes.add_picture(path, Inches(x), Inches(y), Inches(cw), Inches(ch))
        if cur > target:
            excess = (1 - target / cur) / 2; p.crop_left = excess; p.crop_right = excess
        else:
            excess = (1 - cur / target) / 2; p.crop_top = excess; p.crop_bottom = excess
        return p
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return sl.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def notes(sl, t):
    sl.notes_slide.notes_text_frame.text = t


# ------------------------------------------------------------------ 版式
def content_slide(sec_idx, title, subtitle=""):
    sl = prs.slides.add_slide(BLANK); state["page"] += 1
    rect(sl, 0, 0, W, H, WHITE)
    # 顶部导航条
    rect(sl, 0, 0, W, 0.42, NAVY)
    nav_w = 1.25; x0 = W - nav_w * len(SECTIONS) - 0.25
    for i, s in enumerate(SECTIONS):
        if i == sec_idx:
            b = rect(sl, x0 + i * nav_w, 0.0, nav_w, 0.42, CYAN)
        text(sl, x0 + i * nav_w, 0.05, nav_w, 0.32, s, size=11, color=WHITE, bold=(i == sec_idx), align="c", anchor="m")
    text(sl, 0.35, 0.05, 4.5, 0.32, "哨兵 · 公路养护作业区智能预警锥桶", size=11, color=WHITE, anchor="m")
    # 标题
    chip = rect(sl, 0.45, 0.72, 0.62, 0.62, CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    shape_text(chip, f"{sec_idx + 1:02d}", size=18)
    text(sl, 1.22, 0.62, 9.5, 0.6, title, size=26, color=NAVY, bold=True, anchor="m")
    if subtitle:
        text(sl, 1.24, 1.15, 10.5, 0.36, subtitle, size=13, color=GREY)
    rect(sl, 1.24, 1.55, 1.1, 0.05, ORANGE)
    # 页脚
    rect(sl, 0, H - 0.08, W, 0.08, NAVY)
    text(sl, 0.35, H - 0.42, 6, 0.3, f"{COMPETITION} · {CATEGORY}", size=9.5, color=GREY)
    text(sl, W - 1.0, H - 0.42, 0.7, 0.3, str(state["page"]), size=10, color=GREY, align="r")
    return sl


def section_slide(idx, title, claim):
    sl = prs.slides.add_slide(BLANK); state["page"] += 1
    rect(sl, 0, 0, W, H, NAVY2)
    rect(sl, 0, 0, 0.35, H, CYAN)
    text(sl, 1.2, 1.7, 4, 1.8, f"{idx + 1:02d}", size=110, color=CYAN, bold=True)
    text(sl, 1.25, 3.75, 10, 0.9, title, size=40, color=WHITE, bold=True)
    rect(sl, 1.3, 4.75, 1.4, 0.06, ORANGE)
    text(sl, 1.25, 4.95, 10.5, 0.8, claim, size=20, color=RGBColor(0xC9, 0xD8, 0xEE))
    return sl


def card(sl, x, y, w, h, head, body, color=NAVY, head_size=17, body_size=13, icon=None):
    rect(sl, x, y, w, h, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(sl, x, y + 0.15, 0.08, h - 0.3, color)
    text(sl, x + 0.25, y + 0.15, w - 0.4, 0.45, head, size=head_size, color=color, bold=True)
    text(sl, x + 0.25, y + 0.68, w - 0.4, h - 0.8, body, size=body_size, color=INK, spacing=1.2)


def big_number(sl, x, y, w, num, unit, label, color=NAVY, src="", nsize=46):
    text(sl, x, y, w, 0.95, [[(num, {"size": nsize, "bold": True, "color": color}), (" " + unit, {"size": 18 if nsize > 40 else 15, "color": color, "bold": True})]], align="c")
    text(sl, x, y + 1.0, w, 0.7, label, size=13, color=INK, align="c")
    if src:
        text(sl, x, y + 1.55, w, 0.35, src, size=9.5, color=GREY, align="c")


def table(sl, x, y, w, rows, col_w, size=12, row_h=0.46, highlight_col=None):
    shp = sl.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tb = shp.table
    for j, cw in enumerate(col_w):
        tb.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tb.rows[i].height = Inches(row_h)
        for j, v in enumerate(row):
            c = tb.cell(i, j); c.text = ""
            c.margin_left = c.margin_right = Inches(0.06); c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = v; r.font.name = FONT; r.font.size = Pt(size)
            rPr = r._r.get_or_add_rPr(); rPr.append(rPr.makeelement(qn("a:ea"), {"typeface": FONT}))
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = NAVY; r.font.color.rgb = WHITE; r.font.bold = True
            elif highlight_col is not None and j == highlight_col:
                c.fill.fore_color.rgb = RGBColor(0xFF, 0xF1, 0xE3); r.font.color.rgb = RGBColor(0xB4, 0x52, 0x09); r.font.bold = True
            else:
                c.fill.fore_color.rgb = WHITE if i % 2 else BG; r.font.color.rgb = INK
            if v.startswith("【"):
                c.fill.fore_color.rgb = YEL
    return tb


def arrow_right(sl, x, y, w=0.45, h=0.4, color=ORANGE):
    rect(sl, x, y, w, h, color, shape=MSO_SHAPE.RIGHT_ARROW)




def ref(key):
    return f"[{ref_no(key)}]"


def caption(sl, x, y, w, t):
    text(sl, x, y, w, 0.3, t, size=9.5, color=GREY)


def numbered_rows(sl, x, y, w, items, row_h=1.15, colors=None, head_size=15, body_size=11.5):
    colors = colors or [NAVY, CYAN, ORANGE, RED, GREY]
    for i, (h_, b_) in enumerate(items):
        yy = y + i * row_h
        rect(sl, x, yy, w, row_h - 0.12, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        n = rect(sl, x + 0.15, yy + (row_h - 0.12) / 2 - 0.3, 0.6, 0.6, colors[i % len(colors)], shape=MSO_SHAPE.OVAL)
        shape_text(n, str(i + 1), size=16)
        text(sl, x + 0.9, yy + 0.06, w - 1.0, 0.4, h_, size=head_size, color=NAVY, bold=True)
        text(sl, x + 0.9, yy + 0.45, w - 1.0, row_h - 0.55, b_, size=body_size, color=INK, spacing=1.15)


def alpha(shape, val):
    sp = shape.fill._xPr.find(qn("a:solidFill"))[0]
    sp.append(sp.makeelement(qn("a:alpha"), {"val": str(val)}))


# ================================================================== 1 封面
sl = prs.slides.add_slide(BLANK); state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, 8.4, H, NAVY2); alpha(ov, 84000)
rect(sl, 0.6, 0.75, 0.9, 0.9, WHITE, shape=MSO_SHAPE.OVAL)
text(sl, 0.6, 1.0, 0.9, 0.4, "校徽", size=12, color=NAVY, align="c", bold=True)
text(sl, 1.65, 0.85, 6.4, 0.7, f"{COMPETITION}\n{CATEGORY}（B 类）", size=13, color=RGBColor(0xC9, 0xD8, 0xEE))
text(sl, 0.6, 2.2, 7.6, 1.2, "哨  兵", size=60, color=WHITE, bold=True)
text(sl, 0.62, 3.35, 7.6, 1.2, SHORT_TITLE, size=26, color=WHITE, bold=True, spacing=1.2)
rect(sl, 0.65, 4.75, 1.4, 0.07, ORANGE)
text(sl, 0.62, 4.95, 7.4, 0.5, "让锥桶能测到来车、按危险程度提醒", size=18, color=CYAN, bold=True)
text(sl, 0.62, 5.8, 7.6, 1.0, ["答辩人：【填】    团队成员：【填】",
                              f"指导教师：【填】    {SCHOOL}【请核对】"], size=13, color=WHITE, spacing=1.35)
text(sl, 8.6, H - 0.45, 4.6, 0.35, "背景为 AI 生成的概念图，答辩前替换为实物照片", size=9, color=RGBColor(0xDD, 0xDD, 0xDD), align="r")
notes(sl, "各位评委老师好，我们是“哨兵”团队。作品是基于毫米波雷达与协同组网的公路养护作业区智能预警锥桶系统：让锥桶能测到来车，并按危险程度提醒司机和工人。下面按背景问题、方案设计、关键技术、验证情况、创新与计划五部分汇报。")

# ================================================================== 2 目录
sl = prs.slides.add_slide(BLANK); state["page"] += 1
rect(sl, 0, 0, W, H, WHITE)
rect(sl, 0, 0, 4.3, H, NAVY2)
text(sl, 0.6, 2.6, 3.4, 1.0, "目录", size=48, color=WHITE, bold=True)
text(sl, 0.62, 3.6, 3.4, 0.5, "CONTENTS", size=18, color=CYAN, bold=True)
items = [("背景问题", "作业区风险与现有设施的缺口"), ("方案设计", "四类节点 · 三层架构 · 现场布设"),
         ("关键技术", "TTC 分级 · 滤波防误报 · 组网"), ("验证情况", "已完成的软件验证 · 待做的实测"),
         ("创新计划", "作品特点 · 应用路径 · 团队计划")]
for i, (a_, b_) in enumerate(items):
    y = 0.85 + i * 1.22
    chip = rect(sl, 5.0, y, 0.9, 0.9, CYAN if i % 2 else NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.18)
    shape_text(chip, f"{i + 1:02d}", size=22)
    text(sl, 6.15, y + 0.0, 3.0, 0.5, a_, size=22, color=NAVY, bold=True)
    text(sl, 6.17, y + 0.5, 6.5, 0.4, b_, size=13, color=GREY)
notes(sl, "（目录页，带过即可）")

# ================================================================== 3 背景
sl = content_slide(0, "作业区是来车风险集中的地方", "边通车边施工，工人背对来车，现场噪声大")
pic(sl, IMG + "workzone.png", 0.6, 1.9, crop_to=(5.4, 4.3))
caption(sl, 0.6, 6.25, 5.4, "示意图（AI 生成），答辩前替换为团队实地调研照片")
big_number(sl, 6.4, 1.8, 3.2, str(FHWA_2024_DEATHS), "人", f"2024 年美国工作区交通事故死亡\n（2023 年 {FHWA_2023_DEATHS} 人）", RED, f"FHWA-HOP-26-060 {ref('HOP-26-060')}")
big_number(sl, 9.7, 1.8, 3.2, "过半", "", "致死事故发生在夜间；\n追尾约占四分之一", ORANGE, f"同上 {ref('HOP-26-060')}", nsize=40)
big_number(sl, 6.4, 3.9, 3.2, ROAD_KM, "万公里", "我国公路里程（2025 年末）", NAVY, f"交通运输部统计公报 {ref('2025年')}", nsize=38)
big_number(sl, 9.7, 3.9, 3.2, RURAL_KM, "万公里", "其中农村公路", CYAN, f"同上 {ref('2025年')}", nsize=38)
box = rect(sl, 6.4, 5.95, 6.5, 0.85, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
text(sl, 6.55, 6.0, 6.25, 0.8, "美国数据只说明作业区来车风险被持续统计，不能代表我国。\n【待补充：我国作业区事故统计或典型案例及出处】", size=11.5, color=INK)
notes(sl, f"养护作业通常边通车边施工，工人面向路面、背对来车，机械噪声大。美国联邦公路局2026年的资料显示，2024年美国工作区交通事故死亡{FHWA_2024_DEATHS}人，超过一半的致死事故发生在夜间，追尾约占四分之一。这是美国数据，我们只用它说明这类风险被持续统计。我国到2025年末公路里程{ROAD_KM}万公里，其中农村公路{RURAL_KM}万公里，日常小修保养点多面广。【答辩前补充一条国内统计或案例，并注明出处】")

# ================================================================== 4 缺口
sl = content_slide(0, "现有设施能隔离和告知，但看不到来车", "以功能划分，不涉及具体产品的性能和价格")
pains = [("被动", "锥桶、水马、标志牌\n只能隔离和告知", NAVY), ("不分级", "爆闪灯固定频率闪烁\n不区分车辆危险程度", CYAN),
         ("滞后", "入侵报警多在车辆\n越界或碰撞后触发", ORANGE), ("盲区", "工人背对来车\n噪声中难以察觉", RED), ("无记录", "危险接近发生过几次\n事后无法查证", GREY)]
for i, (h_, b_, c_) in enumerate(pains):
    x = 0.6 + i * 2.48
    rect(sl, x, 1.95, 2.25, 3.55, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    ic = rect(sl, x + 0.62, 2.25, 1.0, 1.0, c_, shape=MSO_SHAPE.OVAL); shape_text(ic, str(i + 1), size=26)
    text(sl, x, 3.45, 2.25, 0.6, h_, size=24, color=c_, bold=True, align="c")
    text(sl, x + 0.1, 4.15, 2.05, 1.2, b_, size=13.5, color=INK, align="c", spacing=1.25)
box = rect(sl, 0.6, 5.8, 12.1, 0.95, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
shape_text(box, ["目标：在规范要求的设施之外，给普通锥桶加一层主动提醒——",
                 "测到来车、算出还剩几秒、按危险程度提醒司机和工人，并留下记录"], size=16)
notes(sl, "按功能看，现有设施有五个缺口：隔离设施是被动的；爆闪灯不区分危险程度；入侵报警多在车辆越界或碰撞后才触发；工人背对来车、噪声大，很难察觉；危险接近发生过几次，事后没有记录。我们的目标是在规范要求的设施之外，给普通锥桶加一层主动提醒。")

# ================================================================== 5 依据与定位
sl = content_slide(0, "依据与定位：补充，而不是替代", "标准规定怎么摆，本作品负责“看见来车”")
basis = [(f"JTG H30—2015 {ref('2015年第16号')}", "公路养护安全作业规程：作业区划分与安全设施布设"),
         (f"GB 5768.4—2017 {ref('GB 5768.4')}", "道路交通标志和标线 第 4 部分：作业区"),
         (f"23 CFR 630.1108 {ref('630.1108')}", "美国把入侵报警、速度管理、智能交通系统列为可选措施"),
         (f"FHWA EDC-8 {ref('EDC-8')}", "夜间作业区专题推广自动入侵报警、顺序点亮的警示灯")]
for i, (h_, b_) in enumerate(basis):
    y = 1.9 + i * 1.18
    rect(sl, 0.6, y, 6.6, 1.05, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    rect(sl, 0.6, y + 0.15, 0.08, 0.75, [NAVY, NAVY, CYAN, CYAN][i])
    text(sl, 0.85, y + 0.08, 6.2, 0.4, h_, size=15, color=NAVY, bold=True)
    text(sl, 0.85, y + 0.5, 6.2, 0.5, b_, size=12, color=INK)
layers = [("规范设施", "标志 · 锥桶 · 防撞设施\n按 JTG H30 / GB 5768.4 布设", GREY),
          ("本作品", "测距测速 → TTC 分级\n声光 + 流水灯 + 工人震动", ORANGE),
          ("管理", "接近事件入库\n安全报告 · 复盘", NAVY)]
for i, (h_, b_, c_) in enumerate(layers):
    y = 1.9 + i * 1.58
    s = rect(sl, 7.7, y, 5.0, 1.38, c_, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    text(sl, 7.9, y + 0.1, 1.6, 1.15, h_, size=18, color=WHITE, bold=True, anchor="m")
    text(sl, 9.5, y + 0.12, 3.1, 1.15, b_, size=12.5, color=WHITE, anchor="m")
text(sl, 0.6, 6.6, 12.1, 0.3, "国外已有入侵报警、顺序警示灯等做法，本作品不是首创；特点在于把 TTC 分级、流水灯、工人穿戴端和事件记录集成到低成本锥桶节点。", size=11, color=GREY)
notes(sl, "我们的定位是补充而不是替代。作业区怎么划分、标志和锥桶怎么摆，按JTG H30和GB 5768.4执行；美国联邦法规把入侵报警等技术列为可选措施，联邦公路局夜间作业区专题也在推广自动入侵报警和顺序点亮的警示灯。所以这类思路不是我们首创，我们的特点是把TTC提前分级、流水灯、工人穿戴端和事件记录集成到一个低成本的锥桶节点里。")

# ================================================================== 6 方案总览
sl = content_slide(1, "方案总览：四类节点协同预警", "卡装在标准锥桶顶部 · 不改造现有设施")
pic(sl, IMG + "hero_cone.png", 0.6, 1.9, crop_to=(5.0, 4.55))
caption(sl, 0.6, 6.5, 5.0, "概念渲染图（AI 生成），答辩前替换为样机照片")
roles = [("哨兵锥桶", "24 GHz 雷达测距测速\n计算 TTC，三级预警", ORANGE), ("联动锥桶", "ESP-NOW 接收预警\n错相点亮形成流水灯", CYAN),
         ("工人报警器", "二级预警时\n震动 + 蜂鸣 + 红灯", RED), ("网关与平台", "MQTT 上传 · 事件入库\n实时看板 · 安全报告", NAVY)]
for i, (h_, b_, c_) in enumerate(roles):
    x = 6.0 + (i % 2) * 3.45; y = 1.9 + (i // 2) * 2.4
    card(sl, x, y, 3.25, 2.15, h_, b_, color=c_, body_size=14)
notes(sl, "系统由四类节点组成。上游的哨兵锥桶用毫米波雷达测量来车距离和速度，计算碰撞时间做三级预警；联动锥桶接收预警，按编号错相点亮形成流水灯；工人报警器在最危险的二级预警时震动提醒；网关把数据转成MQTT上传，平台记录每次接近事件并生成安全报告。")

# ================================================================== 7 架构
sl = content_slide(1, "三层架构：感知—边缘决策—平台", "判定全部在锥桶本地完成，网关或平台断开时预警照常工作")
pic(sl, IMG + "arch.png", 1.35, 1.75, h=5.15)
notes(sl, "系统分三层。感知层是雷达、离线语音和电量与环境模式；边缘层由哨兵完成滤波、TTC计算和分级判定，通过ESP-NOW广播给联动锥桶和工人端，最多两跳；网关把报文转成MQTT上传平台。关键设计是判定全部在本地完成，网络中断不影响预警。")

# ================================================================== 8 布设
sl = content_slide(1, "现场布设与使用流程", "按 JTG H30 / GB 5768.4 设置作业区后，把哨兵放在上游、雷达朝来车")
pic(sl, IMG + "layout.png", 1.4, 1.7, w=10.5)
steps = [("放置", "哨兵放在上游\n距离按限速与视距定"), ("启动", "“小哨兵，开始作业”\n语音播报确认"), ("预警", "来车危险时\n声光 + 流水灯 + 震动"), ("收工", "“结束作业”\n平台生成安全报告")]
for i, (h_, b_) in enumerate(steps):
    x = 0.8 + i * 3.1
    rect(sl, x, 5.55, 2.45, 1.25, NAVY if i % 2 == 0 else CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 5.58, 2.45, 0.45, h_, size=17, color=WHITE, bold=True, align="c")
    text(sl, x, 6.0, 2.45, 0.75, b_, size=12, color=WHITE, align="c")
    if i < 3:
        arrow_right(sl, x + 2.53, 5.97)
notes(sl, "现场使用：先按规范设置作业区，再把哨兵放在上游，雷达朝向来车，具体距离按限速和视距确定，图中50到150米只是示意；联动锥桶沿过渡区摆放。对哨兵说“小哨兵，开始作业”启动；有危险时自动声光、流水灯和工人震动；收工说“结束作业”，平台生成安全报告。")

# ================================================================== 9 TTC
sl = content_slide(2, "TTC 与超速双判据，三级分级预警", "TTC = 距离 ÷ 接近速度：车辆保持当前速度还需几秒到达")
pic(sl, IMG + "ttc_map.png", 0.5, 1.75, h=5.15)
rows = [["等级", "触发条件", "锥桶", "工人端"],
        ["安全", f"TTC ≥ {TTC1:g} s 且未超速", "黄灯慢闪", "静默"],
        ["一级", f"TTC < {TTC1:g} s 或车速 > {SPEED_LIMIT}×{OVERSPEED} km/h", "红黄快闪 + 流水灯", "LED 提示"],
        ["二级", f"TTC < {TTC2:g} s", "红色爆闪 + 蜂鸣", "震动 + 蜂鸣"]]
table(sl, 8.4, 1.9, 4.5, rows, [0.65, 1.65, 1.2, 1.0], size=10.5, row_h=0.62)
card(sl, 8.4, 4.6, 4.5, 2.2, "阈值与环境系数", f"TTC 概念见 Hayward（1972）{ref('Hayward')}\n雨天 ×{RAIN}、夜间 ×{NIGHT}，可叠加 ×{RAIN * NIGHT:.2f}\n阈值与系数均为设计初值，需实测标定", color=ORANGE, body_size=12.5)
notes(sl, f"判定用TTC，也就是车辆保持当前速度还需几秒到达，这一概念来自Hayward 1972年的交通冲突研究。TTC小于{TTC1:g}秒或车速超过限速的{OVERSPEED}倍触发一级，小于{TTC2:g}秒触发二级并通知工人。雨天阈值乘{RAIN}，夜间乘{NIGHT}，定性理由是湿滑路面制动距离更长、夜间视距更短。需要说明：这些阈值和系数是设计初值，要靠封闭场地实测来标定。")

# ================================================================== 10 滤波防误报
sl = content_slide(2, "卡尔曼滤波 + 防误报措施", "仿真条件：55 km/h 匀速接近，距离量测噪声 σ = 2 m（理论演示，非实测）")
pic(sl, IMG + "sim_curve.png", 0.5, 1.75, h=5.15)
numbered_rows(sl, 8.4, 1.85, 4.5, [
    ("一维卡尔曼滤波", f"Q=0.5，R=4{ref('Kalman')}，平滑距离/速度跳变"),
    (f"连续 {CONFIRM} 帧确认", "达到条件的帧连续出现才升级"),
    (f"按时间解除（{RELEASE_S:g} s）", "主循环计时，雷达无帧或断线也能解除"),
    ("目标筛选", "只取接近、≥5 km/h、≤100 m 的目标\n多目标取 TTC 最小者")], row_h=1.25)
notes(sl, f"雷达读数会跳，我们用一维卡尔曼滤波平滑，参数Q取0.5、R取4；目标需连续{CONFIRM}帧满足条件才升级；目标消失{RELEASE_S:g}秒后按时间解除，这个判断放在主循环里，雷达无帧甚至串口断开时也能按时解除；只跟踪接近、速度不低于5公里每小时、100米内的目标，多目标取最危险的一个。左图是仿真：55公里每小时已超过48公里每小时的超速线，第3帧即进入一级，TTC降到2.5秒以下时升级二级。这是理论演示，不是实测。")

# ================================================================== 11 组网
sl = content_slide(2, "锥桶自组网：无需路由器的协同联动", f"ESP-NOW 广播{ref('esp_now')}：不依赖路由器和移动网络")
mets = [(f"≤{MAX_HOPS}", "跳", "中继扩大覆盖"), (str(REPEAT_MS), "ms", "预警期间重发间隔"), (str(LINK_TIMEOUT_S), "s", "收不到刷新即回安全"), ("32", "位", "序号 · 按节点去重")]
for i, (n_, u_, l_) in enumerate(mets):
    x = 0.6 + i * 3.1
    rect(sl, x, 1.9, 2.85, 1.85, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    big_number(sl, x, 2.0, 2.85, n_, u_, l_, [ORANGE, NAVY, CYAN, RED][i])
flow_ = [("哨兵", "等级变化立即广播\n预警期间每 200 ms 重发", ORANGE), ("联动锥桶 1", "去重后随机退避\n转发一次", CYAN), ("联动锥桶 2…n", "按编号错相点亮\n形成流水灯", CYAN), ("工人端", "二级预警\n震动 + 蜂鸣", RED), ("网关", "全部报文去重\n转 MQTT 上传", NAVY)]
for i, (h_, b_, c_) in enumerate(flow_):
    x = 0.6 + i * 2.5
    rect(sl, x, 4.2, 2.05, 1.75, c_, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 4.3, 2.05, 0.5, h_, size=16, color=WHITE, bold=True, align="c")
    text(sl, x + 0.05, 4.85, 1.95, 1.0, b_, size=11.5, color=WHITE, align="c")
    if i < 4:
        arrow_right(sl, x + 2.08, 4.85, w=0.38, h=0.36)
text(sl, 0.6, 6.15, 12.1, 0.7, "模式配置包（开始/结束作业、封道方向）同样去重后转发一次，离哨兵较远的锥桶也能切换；心跳与事件不转发，只由网关上传。", size=12.5, color=GREY)
notes(sl, f"组网用ESP-NOW广播，不需要路由器。哨兵等级变化立即广播，预警期间每{REPEAT_MS}毫秒重发；联动锥桶按“节点号加32位序号”去重，随机退避后转发一次，最多{MAX_HOPS}跳；模式配置包也会转发，远处的锥桶同样能切换。联动锥桶和工人端{LINK_TIMEOUT_S}秒收不到刷新就回到安全状态，避免一直报警。网关对所有报文去重后转MQTT上传。")

# ================================================================== 12 工人端与语音
sl = content_slide(2, "预警直达工人，语音一句话部署", "补上“工人背对来车”的感知盲区")
card(sl, 0.6, 1.9, 5.9, 4.9, "工人报警器", f"ESP32-C3 + 振动马达 + 蜂鸣器 + 指示灯\n锂电池供电，可夹在安全帽或反光背心上\n\n一级预警：LED 提示\n二级预警：震动 + 蜂鸣 + 红灯\n{LINK_TIMEOUT_S} s 收不到哨兵刷新自动回到安全\n\n物料估算约 {COST_WORKER} 元【待补充：实际采购价】", color=RED, body_size=14)
rows = [["语音命令", "作用"], ["开始作业 / 结束作业", "启动或收工"], ["左侧封道 / 右侧封道", "流水灯方向"], ["雨天模式开 / 关", f"阈值 ×{RAIN}"], ["夜间模式开 / 关", f"阈值 ×{NIGHT}"], ["报告电量 / 设备自检", "电量是否充足 / 声光自检"]]
table(sl, 6.85, 1.9, 5.9, rows, [3.2, 2.7], size=13, row_h=0.6)
text(sl, 6.85, 5.7, 5.9, 1.0, "ASRPRO 离线识别，唤醒词“小哨兵”；识别结果以 4 字节帧（9600 8N1）发给哨兵。戴手套、无网络也能操作。", size=13, color=NAVY, bold=True)
notes(sl, "工人报警器夹在安全帽或背心上，一级预警亮灯提示，二级预警震动加蜂鸣，解决工人背对来车、现场噪声大的问题；3秒收不到刷新自动回到安全。部署用ASRPRO离线语音，唤醒词是“小哨兵”，可以开始和结束作业、切换封道方向和雨天夜间模式、播报电量是否充足和做声光自检。")

# ================================================================== 13 硬件与成本
sl = content_slide(2, "硬件选型与物料估算", f"哨兵节点约 {COST_SENTINEL} 元 · 演示套装约 {COST_KIT} 元（按常见零售价估算，未含外壳与运费）")
pic(sl, IMG + "hw.png", 0.5, 1.8, w=6.9)
costs = [("哨兵锥桶", COST_SENTINEL, ORANGE), ("联动锥桶", COST_FOLLOWER, CYAN), ("工人报警器", COST_WORKER, RED), ("网关", COST_GATEWAY, NAVY)]
text(sl, 7.8, 1.85, 5, 0.45, "单节点物料估算（元）", size=16, color=NAVY, bold=True)
for i, (n_, v_, c_) in enumerate(costs):
    y = 2.45 + i * 0.72
    text(sl, 7.8, y, 1.6, 0.5, n_, size=13.5, color=INK, anchor="m")
    rect(sl, 9.45, y + 0.08, 2.8 * v_ / COST_SENTINEL, 0.38, c_)
    text(sl, 9.5 + 2.8 * v_ / COST_SENTINEL, y, 0.9, 0.5, str(v_), size=14, color=c_, bold=True, anchor="m")
card(sl, 7.8, 5.4, 5.0, 1.45, "关键器件", f"HLK-LD2451 24 GHz 雷达：标称 ≤100 m{ref('使用手册')}\nESP32-C3：RISC-V，支持 Wi-Fi 与 ESP-NOW\n【待补充：实际采购价与发票】", color=NAVY, head_size=14, body_size=11.5)
notes(sl, f"主控用ESP32-C3，支持ESP-NOW；雷达用海凌科LD2451，24GHz，手册标称最远约100米；电源是18650锂电加5伏升压。按常见零售价估算，哨兵节点约{COST_SENTINEL}元，联动锥桶约{COST_FOLLOWER}元，工人报警器约{COST_WORKER}元，网关约{COST_GATEWAY}元，演示套装约{COST_KIT}元。实际采购价以发票为准。")

# ================================================================== 14 软件验证
sl = content_slide(3, "已完成：软件链路验证", "以下结果均可在仓库中复现（2026-11-01）")
done = [("固件编译", f"四类节点固件\n{CORE}\nFlash 占用 {FLASH_USE}，无编译告警", NAVY),
        ("单元测试", f"Python 参考实现 {TESTS} 项测试通过\n含雷达帧解析、三级判定、\n序号去重、固件/Python 参数对账", CYAN),
        ("端到端联调", "本机 MQTT broker + 模拟器\n→ 平台入库 → 看板 → 安全报告\n全部链路打通", ORANGE)]
for i, (h_, b_, c_) in enumerate(done):
    card(sl, 0.6, 1.85 + i * 1.5, 5.5, 1.38, h_, b_, color=c_, head_size=15, body_size=11.5)
pic(sl, IMG + "dashboard_sim.png", 6.4, 1.85, crop_to=(6.4, 4.4))
caption(sl, 6.4, 6.3, 6.4, "平台看板截图：数据来自模拟器，不是实测")
text(sl, 0.6, 6.4, 5.5, 0.3, "尚未完成：实物样机与封闭场地实测（见第 16 页）", size=11.5, color=RED, bold=True)
notes(sl, f"目前完成的是软件链路验证：四类节点固件在{CORE}下编译通过，Flash占用{FLASH_USE}；Python参考实现{TESTS}项单元测试通过，包括雷达帧解析、三级判定、序号去重，以及固件和Python参数一致性检查；在本机用MQTT服务器加模拟器跑通了平台入库、看板和安全报告。右图看板数据来自模拟器，不是实测。实物样机和封闭场地实测还在进行。")

# ================================================================== 15 理论时间窗
sl = content_slide(3, "理论计算：雷达距离能留出多少时间", "t = 100 m ÷ 车速（按标称最远探测距离，实际距离需实测）")
pic(sl, IMG + "lead_time.png", 0.5, 1.8, h=4.95)
card(sl, 8.6, 1.9, 4.3, 2.4, "计算结果", f"{SPEED_LIMIT} km/h：约 9.0 s\n60 km/h：约 6.0 s\n72 km/h 以上不足 {TTC1:g} s，但已超过 {SPEED_LIMIT}×{OVERSPEED} km/h，按超速触发一级", color=NAVY, body_size=13)
card(sl, 8.6, 4.5, 4.3, 2.3, "局限", "安装高度、车型、天气都会影响实际探测距离\n高速路段可研究前后两个哨兵级联（后续工作）", color=ORANGE, body_size=13)
notes(sl, f"这是理论计算：按雷达标称最远100米，{SPEED_LIMIT}公里每小时约有9秒，60公里每小时约6秒，都大于{TTC1:g}秒的一级阈值；车速超过72公里每小时时不足{TTC1:g}秒，但这时已经超速，会按超速条件提前触发一级。实际探测距离受安装高度、车型和天气影响，要实测确认。")

# ================================================================== 16 实测计划
sl = content_slide(3, "待完成：封闭场地实测计划", "自行车/电动车 ≤30 km/h，专人警戒，不用车辆冲向真人；目标值为团队自定验收线")
rows = [["指标", "目标值", "测试方法", "实测值"],
        ["测速误差", "≤ ±3 km/h", "10～30 km/h 五档各 5 次，对比测速仪", "【待实测】"],
        ["测距误差", "≤ ±2 m", "路面每 10 m 标记，对比雷达读数", "【待实测】"],
        ["最远稳定检测距离", "≥ 80 m", "白天 / 夜间 / 小雨各 5 次", "【待实测】"],
        ["一级预警提前量", "≥ 4 s", "视频逐帧计时", "【待实测】"],
        ["误报率", "≤ 5%", "30 min 无目标驶近观察", "【待实测】"],
        ["漏报率", "≤ 2%", "20 次超阈值驶近", "【待实测】"],
        ["联动延迟", "≤ 100 ms", "慢动作视频逐帧，10 次", "【待实测】"],
        ["续航", "≥ 8 h", "满电连续运行", "【待实测】"]]
table(sl, 0.9, 1.9, 11.5, rows, [2.8, 2.0, 4.6, 2.1], size=14, row_h=0.53)
notes(sl, "这是封闭场地实测计划，目标值是团队自己定的验收线。测试只在封闭场地用自行车或电动车，车速不超过30公里每小时，专人警戒。【实测完成后把黄色格子替换为实测数据，口头说明测试日期、地点和次数】")

# ================================================================== 17 创新点
sl = content_slide(4, "作品特点", "不是首创某项技术，而是面向小型养护作业的低成本集成")
inn = [("按危险程度提醒", f"TTC + 超速双判据分级\n平时慢闪、危险时才升级", ORANGE), ("流水灯引导", "联动锥桶错相点亮\n指示变道方向", CYAN),
       ("预警直达工人", "二级预警送到工人身上\n弥补背对来车的盲区", RED), ("一句话部署", "离线语音切换作业、\n封道方向和环境模式", NAVY),
       ("断网可用", "判定在锥桶本地完成\n组网不依赖路由器", NAVY), ("接近事件可追溯", "每次危险接近入库\n自动生成安全报告", CYAN)]
for i, (h_, b_, c_) in enumerate(inn):
    x = 0.6 + (i % 3) * 4.1; y = 1.85 + (i // 3) * 2.5
    rect(sl, x, y, 3.85, 2.25, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(sl, x, y, 3.85, 0.12, c_)
    text(sl, x + 0.25, y + 0.3, 1.0, 0.75, f"{i + 1:02d}", size=34, color=c_, bold=True)
    text(sl, x + 1.25, y + 0.42, 2.55, 0.5, h_, size=19, color=NAVY, bold=True)
    text(sl, x + 0.25, y + 1.15, 3.45, 1.0, b_, size=13, color=INK, spacing=1.25)
notes(sl, "总结六个特点：按危险程度提醒、流水灯引导、预警直达工人、一句话部署、断网可用、接近事件可追溯。我们不说首创某项技术，价值在于把这些功能集成到小型养护作业用得上的低成本锥桶里。")

# ================================================================== 18 功能定位对比
sl = content_slide(4, "功能定位对比", "按工作原理比较，不代表具体产品；价格待市场调研后补充")
rows = [["对比项", "锥桶 / 标志", "爆闪警示灯", "入侵报警类", "哨兵（本作品）"],
        ["工作方式", "隔离、告知", "固定频率闪烁", "检测越界或碰撞", "测距测速，计算 TTC"],
        ["触发时机", "—", "常亮 / 常闪", "车辆越界后", "车辆接近途中分级"],
        ["提醒对象", "司机", "司机", "工人（视产品而定）", "司机 + 工人"],
        ["数据记录", "无", "无", "视产品而定", "接近事件入库、报告"],
        ["参考成本", "—", "【待补充】", "【待补充】", f"物料估算约 {COST_KIT} 元/套"]]
table(sl, 0.7, 1.9, 11.9, rows, [2.0, 2.2, 2.3, 2.7, 2.7], size=14, row_h=0.66, highlight_col=4)
text(sl, 0.7, 6.1, 11.9, 0.7, f"入侵报警技术评估见 Gambatese 等（2017）{ref('32574')}；本作品同样需要实测证明效果。【待补充：国内在售产品的名称、参数、价格及出处】", size=12, color=GREY)
notes(sl, "按工作原理比较：锥桶和标志负责隔离告知；爆闪灯固定频率闪烁；入侵报警类多在车辆越界后触发。本作品在车辆接近途中就按TTC分级，同时提醒司机和工人，并留下记录。各类产品价格我们还在调研，没有数据之前不做价格比较。")

# ================================================================== 19 应用前景
sl = content_slide(4, "应用场景与推广路径", f"数据来源：交通运输部《2025年交通运输行业发展统计公报》{ref('2025年')}")
big_number(sl, 0.5, 1.9, 3.1, ROAD_KM, "万公里", "全国公路里程", NAVY, nsize=38)
big_number(sl, 3.6, 1.9, 3.1, RURAL_KM, "万公里", f"农村公路（县道 {COUNTY_KM}、\n乡道 {TOWNSHIP_KM}、村道 {VILLAGE_KM}）", ORANGE, nsize=38)
big_number(sl, 6.7, 1.9, 3.1, EXPRESSWAY_KM, "万公里", "高速公路", CYAN, nsize=38)
card(sl, 10.0, 1.9, 2.9, 2.1, "政策方向", f"交通强国建设纲要{ref('交通强国')}\n公路数字化转型意见{ref('131')}\n安全生产治本攻坚{ref('治本攻坚')}", color=RED, head_size=15, body_size=11.5)
path = [("校内", "样机演示\n封闭场地实测"), ("试用", "联系养护单位\n短期作业试用"), ("改进", "按反馈标定阈值\n优化外壳与续航"), ("推广", "小批量制作\n形成使用指南")]
for i, (h_, b_) in enumerate(path):
    x = 0.6 + i * 3.1
    rect(sl, x, 4.4, 2.6, 1.5, NAVY if i % 2 == 0 else CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 4.5, 2.6, 0.5, h_, size=18, color=WHITE, bold=True, align="c")
    text(sl, x, 5.0, 2.6, 0.8, b_, size=12.5, color=WHITE, align="c")
    if i < 3:
        arrow_right(sl, x + 2.63, 4.95)
text(sl, 0.6, 6.15, 12.2, 0.6, "适用对象：公路养护、市政养护和占道施工单位。【待补充：已联系的养护单位及试用意向（如有）】", size=13, color=NAVY, bold=True)
notes(sl, f"到2025年末，全国公路里程{ROAD_KM}万公里，其中农村公路{RURAL_KM}万公里，高速公路{EXPRESSWAY_KM}万公里，日常小修保养点多面广。作品方向与交通强国建设纲要、公路数字化转型意见和安全生产治本攻坚行动一致。推广分四步：校内样机与实测、联系养护单位试用、按反馈改进、小批量制作。【有试用意向时在此补充】")

# ================================================================== 20 不足与团队
sl = content_slide(4, "不足、下一步与团队", "")
gaps = [("实测数据", "完成封闭场地测试，标定阈值与环境系数"), ("方向判别", "LD2451 接近/远离方向需实机核对"),
        ("通信安全", "ESP-NOW 广播未加密，计划加入报文校验与配对"), ("工程化", "外壳防水、续航测试、PCB 一体化")]
numbered_rows(sl, 0.6, 1.85, 6.3, gaps, row_h=1.2, head_size=15, body_size=12)
text(sl, 7.3, 1.85, 5.6, 0.45, "团队分工", size=17, color=NAVY, bold=True)
rows = [["成员", "专业", "分工"], ["【填】（负责人）", "【填】", "需求调研 · 预警算法 · 申报书"],
        ["【填】", "【填】", "硬件 · 电路 · 固件"], ["【填】", "【填】", "组网 · 平台"], ["【填】", "【填】", "外壳 · 调研 · 答辩"]]
table(sl, 7.3, 2.35, 5.6, rows, [1.7, 1.2, 2.7], size=12, row_h=0.55)
text(sl, 7.3, 5.25, 5.6, 1.5, ["指导教师：【填】", "专利 / 软著 / 获奖：【填：没有就写“暂无”】"], size=13, color=INK, spacing=1.4)
notes(sl, "作品目前还有不足：缺少实测数据，阈值需要标定；雷达接近和远离方向的判别要实机核对；ESP-NOW广播没有加密，计划加入校验和配对；外壳防水、续航和PCB一体化还要做。团队分工如右表。【团队信息、指导教师和成果按实际填写】")

# ================================================================== 21 参考资料
sl = content_slide(4, "参考资料", "均为公开资料，已逐条打开核对（2026-11-01）")
lines = [f"[{i}] {t_}" for i, (t_, _) in enumerate(REFS, start=1)]
half = (len(lines) + 1) // 2
text(sl, 0.6, 1.8, 6.0, 5.1, lines[:half], size=11.5, color=INK, spacing=1.15)
text(sl, 6.85, 1.8, 6.0, 5.1, lines[half:], size=11.5, color=INK, spacing=1.15)
notes(sl, "参考资料列表，链接见申报书参考文献。")

# ================================================================== 22 结束
sl = prs.slides.add_slide(BLANK); state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, W, H, NAVY2); alpha(ov, 80000)
text(sl, 0, 2.3, W, 1.2, "让锥桶测到来车，让提醒早几秒", size=44, color=WHITE, bold=True, align="c")
rect(sl, W / 2 - 0.8, 3.65, 1.6, 0.07, ORANGE)
text(sl, 0, 3.95, W, 0.7, "守护养护工人平安回家", size=22, color=CYAN, align="c", bold=True)
text(sl, 0, 5.3, W, 0.6, "恳请各位评委老师批评指正", size=20, color=WHITE, align="c")
notes(sl, "我们希望让锥桶测到来车，让提醒早几秒，守护养护工人平安回家。汇报完毕，恳请各位评委老师批评指正。")

out = "./哨兵_挑战杯答辩PPT.pptx"
prs.save(out)
print(out, state["page"])
