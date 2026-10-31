# -*- coding: utf-8 -*-
"""挑战杯答辩 PPT：国赛答辩常见的“科技蓝 + 导航条 + 卡片 + 大数字”风格"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from PIL import Image

IMG = "img/"
NAVY = RGBColor(0x0B, 0x2A, 0x5B); NAVY2 = RGBColor(0x06, 0x1A, 0x3A)
CYAN = RGBColor(0x18, 0xA7, 0xE0); ORANGE = RGBColor(0xF2, 0x8C, 0x28); RED = RGBColor(0xE5, 0x39, 0x35)
WHITE = RGBColor(255, 255, 255); BG = RGBColor(0xF4, 0xF7, 0xFB); GREY = RGBColor(0x5B, 0x6B, 0x82)
LIGHT = RGBColor(0xE3, 0xEC, 0xF7); INK = RGBColor(0x1E, 0x29, 0x3B); YEL = RGBColor(0xFF, 0xF2, 0x9E)
FONT = "微软雅黑"
SECTIONS = ["研究背景", "解决方案", "核心技术", "测试验证", "应用价值", "团队成果"]

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
        for seg, opt in segs:
            r = p.add_run(); r.text = seg
            f = r.font; f.name = FONT; f.size = Pt(opt.get("size", size)); f.bold = opt.get("bold", bold)
            f.color.rgb = opt.get("color", color)
            r._r.get_or_add_rPr().set("lang", "zh-CN")
            rPr = r._r.get_or_add_rPr()
            ea = rPr.find(qn("a:ea"))
            if ea is None:
                ea = rPr.makeelement(qn("a:ea"), {}); rPr.append(ea)
            ea.set("typeface", FONT)
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
    text(sl, 0.35, H - 0.42, 6, 0.3, "第二十届“挑战杯”全国大学生课外学术科技作品竞赛 · 科技发明制作类", size=9.5, color=GREY)
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
            if v.startswith("【填"):
                c.fill.fore_color.rgb = YEL
    return tb


def arrow_right(sl, x, y, w=0.45, h=0.4, color=ORANGE):
    rect(sl, x, y, w, h, color, shape=MSO_SHAPE.RIGHT_ARROW)


# ================================================================== 1 封面
sl = prs.slides.add_slide(BLANK); state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, 8.4, H, NAVY2)
ov.fill.fore_color.rgb = NAVY2
# 透明度
sp = ov.fill._xPr.find(qn("a:solidFill"))[0]; a = sp.makeelement(qn("a:alpha"), {"val": "82000"}); sp.append(a)
rect(sl, 0.6, 0.75, 0.9, 0.9, WHITE, shape=MSO_SHAPE.OVAL)
text(sl, 0.6, 1.0, 0.9, 0.4, "校徽", size=12, color=NAVY, align="c", bold=True)
text(sl, 1.65, 0.85, 6.0, 0.7, "第二十届“挑战杯”全国大学生课外学术科技作品竞赛\n科技发明制作类", size=13, color=RGBColor(0xC9, 0xD8, 0xEE))
text(sl, 0.6, 2.2, 7.6, 1.2, "哨  兵", size=60, color=WHITE, bold=True)
text(sl, 0.62, 3.35, 7.6, 1.2, "基于毫米波雷达与协同组网的\n公路养护作业区智能预警锥桶系统", size=26, color=WHITE, bold=True, spacing=1.2)
rect(sl, 0.65, 4.75, 1.4, 0.07, ORANGE)
text(sl, 0.62, 4.95, 7.4, 0.5, "让每一个锥桶都能“看见”危险", size=18, color=CYAN, bold=True)
text(sl, 0.62, 5.9, 7.6, 0.9, ["答辩人：【填】    团队成员：【填】", "指导教师：【填】    山东理工大学 交通与车辆工程学院"], size=13, color=WHITE, spacing=1.35)
text(sl, 8.6, H - 0.45, 4.6, 0.35, "图为产品概念渲染，答辩前替换为实物照片", size=9, color=RGBColor(0xDD, 0xDD, 0xDD), align="r")
notes(sl, "各位评委老师好，我们是“哨兵”团队。我们的作品是基于毫米波雷达与协同组网的公路养护作业区智能预警锥桶系统，一句话概括：让每一个锥桶都能看见危险。下面从研究背景、解决方案、核心技术、测试验证、应用价值和团队成果六个方面汇报。")

# ================================================================== 2 目录
sl = prs.slides.add_slide(BLANK); state["page"] += 1
rect(sl, 0, 0, W, H, WHITE)
rect(sl, 0, 0, 4.3, H, NAVY2)
text(sl, 0.6, 2.6, 3.4, 1.0, "目录", size=48, color=WHITE, bold=True)
text(sl, 0.62, 3.6, 3.4, 0.5, "CONTENTS", size=18, color=CYAN, bold=True)
items = [("研究背景", "作业区为什么危险"), ("解决方案", "四类节点协同预警"), ("核心技术", "TTC 分级 · 滤波 · 组网"),
         ("测试验证", "编译 · 联调 · 仿真 · 实测"), ("应用价值", "市场 · 政策 · 效益"), ("团队成果", "分工 · 知识产权")]
for i, (a_, b_) in enumerate(items):
    col, row = i % 2, i // 2
    x = 5.0 + col * 4.1; y = 1.1 + row * 1.95
    chip = rect(sl, x, y, 0.95, 0.95, CYAN if i % 3 else NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.18)
    shape_text(chip, f"{i + 1:02d}", size=24)
    text(sl, x + 1.15, y + 0.02, 2.9, 0.5, a_, size=22, color=NAVY, bold=True)
    text(sl, x + 1.17, y + 0.55, 2.9, 0.4, b_, size=13, color=GREY)
notes(sl, "（目录页，2 秒带过）")

# ================================================================== 3 痛点数据
sl = content_slide(0, "作业区是道路安全最脆弱的地方", "边通车边施工，工人背对来车，事故后果严重")
pic(sl, IMG + "workzone.png", 0.6, 1.9, crop_to=(5.6, 4.6))
text(sl, 0.6, 6.52, 5.6, 0.3, "示意图（AI 生成），答辩前替换为团队实地调研照片", size=9, color=GREY)
big_number(sl, 6.6, 1.95, 3.1, "850", "人", "2024 年美国作业区\n交通事故死亡人数", RED, "来源：FHWA，2026")
big_number(sl, 9.9, 1.95, 3.1, "22", "%", "致死事故涉及追尾", ORANGE, "来源：FHWA，2026")
big_number(sl, 6.6, 4.2, 3.1, ">50", "%", "致死事故发生在夜间", NAVY, "来源：FHWA，2026")
big_number(sl, 9.9, 4.2, 3.1, "549.04", "万公里", "我国公路总里程\n（2024 年末）", CYAN, "来源：交通运输部统计公报", nsize=40)
notes(sl, "养护作业通常是边通车边施工。工人面向路面、背对来车，机械噪声又大，往往车到跟前才发现。美国联邦公路管理局数据显示，2024年美国作业区事故造成850人死亡，约22%的致死事故涉及追尾，超过一半发生在夜间。我国公路总里程已达549.04万公里，养护作业点多面广。【建议补充一条国内作业区事故案例或统计】")

# ================================================================== 4 现有设施不足
sl = content_slide(0, "现有防护“看不见”来车风险", "从调研中总结的五个痛点")
pains = [("被动", "锥桶、水马、标志牌\n只能隔离提示", NAVY), ("同质", "爆闪灯固定频率闪\n司机习惯性忽略", CYAN),
         ("滞后", "入侵报警器\n车已闯入才报警", ORANGE), ("昂贵", "智慧作业区系统\n价格高、安装复杂", RED), ("无数据", "作业区多危险\n无法量化", GREY)]
for i, (h_, b_, c_) in enumerate(pains):
    x = 0.6 + i * 2.48
    rect(sl, x, 2.0, 2.25, 3.6, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    ic = rect(sl, x + 0.62, 2.3, 1.0, 1.0, c_, shape=MSO_SHAPE.OVAL); shape_text(ic, str(i + 1), size=26)
    text(sl, x, 3.5, 2.25, 0.6, h_, size=24, color=c_, bold=True, align="c")
    text(sl, x + 0.1, 4.2, 2.05, 1.2, b_, size=13.5, color=INK, align="c", spacing=1.25)
box = rect(sl, 0.6, 5.95, 12.1, 0.8, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
shape_text(box, "县乡道路、城市道路的日常小型养护，缺少“用得起、即放即用”的主动预警设备", size=18)
notes(sl, "我们调研发现现有防护有五个痛点：被动、同质、滞后、昂贵、无数据。高速公路大型作业可以配智慧作业区系统和防撞缓冲车，但量大面广的县乡道路、城市道路日常小型养护，缺少用得起、拿来就能用的主动预警设备。这就是我们要解决的问题。")

# ================================================================== 5 方案总览
section_slide(1, "解决方案", "给锥桶装上“眼睛、大脑和嗓子”，四类节点协同预警")
sl = content_slide(1, "百元级智能锥桶 让作业区主动预警", "卡装在标准锥桶顶部 · 不改造现有设施 · 一人即可布设")
pic(sl, IMG + "hero_cone.png", 0.6, 1.9, crop_to=(5.0, 4.75))
roles = [("哨兵锥桶", "毫米波雷达测距测速\n计算 TTC，三级预警", ORANGE), ("联动锥桶", "ESP-NOW 接收预警\n流水灯引导变道", CYAN),
         ("工人报警器", "二级预警震动+蜂鸣\n提醒撤离", RED), ("安全平台", "事件入库、实时看板\n自动生成安全报告", NAVY)]
for i, (h_, b_, c_) in enumerate(roles):
    x = 6.0 + (i % 2) * 3.45; y = 1.9 + (i // 2) * 2.45
    card(sl, x, y, 3.25, 2.2, h_, b_, color=c_, body_size=14)
notes(sl, "我们的方案是给锥桶装上眼睛、大脑和嗓子。系统由四类节点组成：上游的哨兵锥桶用毫米波雷达测量来车距离和速度，计算碰撞时间做三级预警；联动锥桶接收预警，依次点亮形成流水灯；工人佩戴报警器，最危险时震动提醒撤离；平台记录每次危险接近，自动生成安全报告。")

# ================================================================== 6 架构
sl = content_slide(1, "三层架构 感知—决策—平台", "判定全部在锥桶本地完成，断网也能预警")
pic(sl, IMG + "arch.png", 1.35, 1.75, h=5.15)
notes(sl, "系统分三层。感知层是雷达、语音和电量环境模式；边缘层由哨兵完成滤波、TTC计算和分级判定，通过ESP-NOW广播给联动锥桶和工人端；网关把数据转成MQTT上传平台。关键设计是判定全部在本地完成，网络中断也不影响预警。")

# ================================================================== 7 布设与流程
sl = content_slide(1, "现场布设 一句话启动", "按 GB 5768.4 设置作业区后，把哨兵放在上游警告区")
pic(sl, IMG + "layout.png", 1.4, 1.7, w=10.5)
steps = [("放置", "哨兵在上游\n50–150 m"), ("启动", "说“开始作业”\n语音确认"), ("预警", "来车危险时\n声光+震动"), ("收工", "说“结束作业”\n自动出报告")]
for i, (h_, b_) in enumerate(steps):
    x = 0.8 + i * 3.1
    c = rect(sl, x, 5.6, 2.45, 1.2, NAVY if i % 2 == 0 else CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 5.63, 2.45, 0.45, h_, size=17, color=WHITE, bold=True, align="c")
    text(sl, x, 6.05, 2.45, 0.7, b_, size=12, color=WHITE, align="c")
    if i < 3:
        arrow_right(sl, x + 2.53, 6.0)
notes(sl, "现场使用很简单：按国标设置作业区后，把哨兵放在上游警告区50到150米处，雷达朝向来车；联动锥桶沿过渡区摆放。对哨兵说“开始作业”就启动，有危险自动声光震动，收工说“结束作业”，平台自动出报告。")

# ================================================================== 8 TTC
section_slide(2, "核心技术", "从“有没有车”升级为“有多危险”")
sl = content_slide(2, "TTC 与超速双判据 三级分级预警", "TTC = 距离 ÷ 接近速度：车辆不减速还剩几秒到达")
pic(sl, IMG + "ttc_map.png", 0.5, 1.75, h=5.15)
rows = [["等级", "触发条件", "锥桶", "工人端"],
        ["安全", "TTC ≥ 5 s 且未超速", "黄灯慢闪", "静默"],
        ["一级", "TTC < 5 s 或超限速 20%", "红黄快闪+流水灯", "LED 提示"],
        ["二级", "TTC < 2.5 s", "红色爆闪+蜂鸣", "强震动+蜂鸣"]]
table(sl, 8.45, 1.95, 4.45, rows, [0.65, 1.6, 1.2, 1.0], size=10.5, row_h=0.62)
card(sl, 8.6, 4.75, 4.3, 2.05, "环境自适应", "雨天阈值 ×1.4（制动距离变长）\n夜间阈值 ×1.2（反应时间变长）\n叠加 ×1.68，语音一键切换", color=ORANGE, body_size=13)
notes(sl, "核心技术一是TTC与超速双判据。TTC是交通冲突技术中衡量碰撞紧迫性的经典指标，就是车辆不减速还剩几秒到达。TTC小于5秒或超速20%触发一级，小于2.5秒触发二级并通知工人撤离。雨天阈值乘1.4，夜间乘1.2，因为湿滑路面制动距离更长、夜间反应更慢。")

# ================================================================== 9 滤波与防误报
sl = content_slide(2, "卡尔曼滤波加三重防误报 预警稳而准", "仿真：距离量测噪声 σ = 2 m，55 km/h 来车")
pic(sl, IMG + "sim_curve.png", 0.5, 1.75, h=5.15)
items_ = [("卡尔曼滤波", "平滑距离与速度跳变，TTC 不因单帧异常误触发"), ("连续 3 帧确认", "约 0.3 s 内确认后才升级"),
          ("1.5 s 保持", "目标短暂丢失不闪断"), ("目标筛选", "只跟踪接近、≥5 km/h、≤100 m 的目标，多目标取 TTC 最小")]
for i, (h_, b_) in enumerate(items_):
    y = 1.85 + i * 1.25
    rect(sl, 8.4, y, 4.5, 1.1, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    n = rect(sl, 8.55, y + 0.25, 0.6, 0.6, [NAVY, CYAN, ORANGE, RED][i], shape=MSO_SHAPE.OVAL); shape_text(n, str(i + 1), size=16)
    text(sl, 9.3, y + 0.08, 3.5, 0.4, h_, size=15, color=NAVY, bold=True)
    text(sl, 9.3, y + 0.48, 3.55, 0.6, b_, size=11.5, color=INK)
notes(sl, "核心技术二是稳定性。雷达读数会跳，我们用卡尔曼滤波平滑；再加连续3帧确认、目标消失后保持1.5秒、只跟踪接近目标三重措施。左图是仿真：在2米量测噪声下，滤波曲线平滑跟踪，系统因超速很快进入一级预警，TTC降到2.5秒时升级二级，全程没有误降级。")

# ================================================================== 10 组网
sl = content_slide(2, "锥桶自组网 毫秒级联动形成流水灯", "ESP-NOW 广播：不需要路由器和流量卡")
mets = [("≤2", "跳", "中继扩大覆盖"), ("200", "ms", "预警期间重发间隔"), ("2–15", "ms", "随机退避转发"), ("32", "位", "序号去重")]
for i, (n_, u_, l_) in enumerate(mets):
    x = 0.6 + i * 3.1
    rect(sl, x, 1.95, 2.85, 1.85, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    big_number(sl, x, 2.05, 2.85, n_, u_, l_, [ORANGE, NAVY, CYAN, RED][i])
flow_ = [("哨兵", "等级变化\n立即广播", ORANGE), ("联动锥桶 1", "去重后转发\n延时点亮", CYAN), ("联动锥桶 2…n", "依次点亮\n形成流水灯", CYAN), ("工人端", "二级预警\n震动+蜂鸣", RED), ("网关", "转 MQTT\n上传平台", NAVY)]
for i, (h_, b_, c_) in enumerate(flow_):
    x = 0.6 + i * 2.5
    s = rect(sl, x, 4.35, 2.05, 1.75, c_, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 4.45, 2.05, 0.5, h_, size=16, color=WHITE, bold=True, align="c")
    text(sl, x, 5.0, 2.05, 0.9, b_, size=12.5, color=WHITE, align="c")
    if i < 4:
        arrow_right(sl, x + 2.08, 5.0, w=0.38, h=0.36)
text(sl, 0.6, 6.35, 12.1, 0.4, "节点上电以随机序号起始，重启后不会被误判为旧包；网关按“节点+序号”去重，经中继也能完整上报", size=12.5, color=GREY)
notes(sl, "核心技术三是组网。我们用ESP-NOW广播，不需要路由器。哨兵等级变化立即广播，预警期间每200毫秒重发；联动锥桶收到后随机退避2到15毫秒转发，最多两跳；所有节点按序号去重。联动锥桶按位置延时点亮，形成指向变道方向的流水灯，比单点爆闪更醒目。")

# ================================================================== 11 工人端与语音
sl = content_slide(2, "预警直达工人 语音一句话部署", "补上“工人背对来车”的感知盲区")
card(sl, 0.6, 1.95, 5.9, 4.8, "工人报警器", "ESP32-C3 + 扁平振动马达 + 蜂鸣器\n500 mAh 锂电，夹在安全帽或反光背心上\n\n二级预警：强震动 + 蜂鸣 + 红灯\n噪声大、背对来车时也能第一时间感知\n\n成本约 31 元", color=RED, body_size=15)
rows = [["语音命令", "作用"], ["开始作业 / 结束作业", "启动或收工"], ["左侧封道 / 右侧封道", "流水灯方向"], ["雨天模式开 / 关", "阈值 ×1.4"], ["夜间模式开 / 关", "阈值 ×1.2"], ["报告电量", "语音播报电量"]]
table(sl, 6.85, 1.95, 5.9, rows, [3.2, 2.7], size=13, row_h=0.62)
text(sl, 6.85, 5.85, 5.9, 0.9, "ASRPRO 离线识别：无网络、戴手套、站在路上都能操作", size=14, color=NAVY, bold=True)
notes(sl, "核心技术四是人机交互。工人报警器夹在安全帽或背心上，二级预警时强震动加蜂鸣，解决工人背对来车、现场噪声大的问题。部署用离线语音，戴着手套站在路上，一句话就能开始作业、切换封道方向和天气模式。")

# ================================================================== 12 硬件与成本
sl = content_slide(2, "硬件选型兼顾性能与成本", "哨兵节点约 115 元 · 演示套装约 350 元（按淘宝常见价估算）")
pic(sl, IMG + "hw.png", 0.5, 1.8, w=6.9)
costs = [("哨兵锥桶", 115, ORANGE), ("联动锥桶", 45, CYAN), ("工人报警器", 31, RED), ("网关", 12, NAVY)]
text(sl, 7.8, 1.85, 5, 0.45, "单节点物料成本（元）", size=16, color=NAVY, bold=True)
for i, (n_, v_, c_) in enumerate(costs):
    y = 2.45 + i * 0.75
    text(sl, 7.8, y, 1.6, 0.5, n_, size=13.5, color=INK, anchor="m")
    rect(sl, 9.45, y + 0.08, 3.0 * v_ / 115, 0.38, c_)
    text(sl, 9.5 + 3.0 * v_ / 115, y, 0.9, 0.5, str(v_), size=14, color=c_, bold=True, anchor="m")
card(sl, 7.8, 5.55, 5.0, 1.3, "关键器件", "LD2451 24GHz 雷达：≤100 m，±15°，5 V/>200 mA\nESP32-C3：RISC-V，原生 ESP-NOW", color=NAVY, head_size=14, body_size=11.5)
notes(sl, "硬件上，主控用ESP32-C3，原生支持ESP-NOW；雷达用海凌科LD2451，24GHz调频连续波，最远探测100米、水平正负15度，专为车辆检测设计；电源是18650锂电加5V升压，满足雷达供电。哨兵节点约115元，一整套演示系统约350元。")

# ================================================================== 13 验证
section_slide(3, "测试验证", "软件已闭环 · 实测数据持续补充")
sl = content_slide(3, "软件链路已全部打通", "固件编译 · 平台联调 · 算法仿真")
done = [("固件编译通过", "四类节点固件\nArduino-ESP32 3.3.12\nFlash 占用 73%–74%", NAVY),
        ("平台端到端联调", "MQTT → SQLite → 看板\n→ 安全报告\n全部接口正常", CYAN),
        ("算法仿真", "σ=2 m 噪声下稳定跟踪\n超速即刻一级预警\nTTC<2.5 s 升级二级", ORANGE)]
for i, (h_, b_, c_) in enumerate(done):
    x = 0.6 + i * 2.15
    rect(sl, x, 1.95, 1.95, 4.8, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    ok = rect(sl, x + 0.62, 2.15, 0.7, 0.7, c_, shape=MSO_SHAPE.OVAL); shape_text(ok, "✓", size=22)
    text(sl, x + 0.05, 3.0, 1.85, 0.8, h_, size=14.5, color=c_, bold=True, align="c")
    text(sl, x + 0.05, 3.85, 1.85, 2.6, b_, size=11.5, color=INK, align="c", spacing=1.3)
pic(sl, IMG + "lead_time.png", 7.15, 1.85, w=5.75)
text(sl, 7.2, 5.6, 5.7, 1.2, "40 km/h 时雷达可提供约 9.0 s 预警窗口，60 km/h 约 6.0 s；高于约 72 km/h 时建议双哨兵级联", size=13, color=NAVY, bold=True, spacing=1.25)
notes(sl, "目前软件链路已全部打通：四类节点固件编译通过；平台用模拟器完成了端到端联调；算法做了仿真。右图是理论分析，雷达最远100米，在40公里每小时的作业区限速下能提供约9秒预警窗口，60公里约6秒，都大于5秒的一级阈值；车速更高时我们设计了双哨兵级联方案。")

sl = content_slide(3, "封闭场地实测指标", "电动车/自行车 ≤30 km/h，专人警戒，不冲撞真人")
rows = [["指标", "目标值", "测试方法", "实测值"],
        ["测速误差", "≤ ±3 km/h", "五档车速各 5 次，对比测速仪", "【填】"],
        ["测距误差", "≤ ±2 m", "路面每 10 m 标记", "【填】"],
        ["最远稳定检测", "≥ 80 m", "白天/夜间/小雨各 5 次", "【填】"],
        ["一级预警提前量", "≥ 4 s", "慢动作视频逐帧计时", "【填】"],
        ["误报率", "≤ 5%", "30 min 无目标驶近", "【填】"],
        ["漏报率", "≤ 2%", "20 次超阈值驶近", "【填】"],
        ["联动延迟", "≤ 100 ms", "慢动作视频逐帧 10 次", "【填】"],
        ["续航", "≥ 8 h", "满电连续运行", "【填】"]]
table(sl, 0.9, 1.9, 11.5, rows, [2.6, 2.2, 4.6, 2.1], size=14, row_h=0.53)
notes(sl, "这是封闭场地实测方案和指标。测试只在封闭场地用电动车或自行车进行，车速不超过30公里每小时，专人警戒。【实测完成后把黄色格子替换为实测数据，并在这一页口头强调最亮眼的一两个数字】")

# ================================================================== 15 创新点
section_slide(4, "创新与价值", "低成本 · 主动 · 协同 · 可量化")
sl = content_slide(4, "六大创新点", "")
inn = [("主动感知", "标准锥桶卡装雷达灯头\n让作业区“看得见”来车", NAVY), ("分级预警", "TTC+超速双判据\n雨天、夜间自适应", ORANGE),
       ("协同组网", "无基础设施广播组网\n去重+两跳中继+流水灯", CYAN), ("工人直达", "震动+声音送到工人身上\n弥补背对来车盲区", RED),
       ("语音部署", "离线识别 一句话\n完成启动与模式切换", NAVY), ("风险量化", "记录每次危险接近\n形成可追溯安全台账", CYAN)]
for i, (h_, b_, c_) in enumerate(inn):
    x = 0.6 + (i % 3) * 4.1; y = 1.85 + (i // 3) * 2.5
    rect(sl, x, y, 3.85, 2.25, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(sl, x, y, 3.85, 0.12, c_)
    text(sl, x + 0.25, y + 0.3, 1.0, 0.75, f"{i + 1:02d}", size=34, color=c_, bold=True)
    text(sl, x + 1.3, y + 0.42, 2.45, 0.5, h_, size=20, color=NAVY, bold=True)
    text(sl, x + 0.25, y + 1.15, 3.45, 1.0, b_, size=13, color=INK, spacing=1.25)
notes(sl, "总结六个创新点：主动感知、分级预警、协同组网、工人直达、语音部署和风险量化。")

sl = content_slide(4, "与现有方案相比 优势明显", "")
rows = [["对比项", "爆闪灯", "入侵报警器", "智慧作业区系统", "哨兵（本作品）"],
        ["感知来车", "×", "闯入后", "√", "√ 100 m 内"],
        ["危险分级", "×", "×", "部分", "√ 三级"],
        ["提醒工人", "×", "√", "部分", "√ 震动直达"],
        ["部署难度", "低", "中", "高（专业安装）", "低（即放即用）"],
        ["数据记录", "×", "×", "√", "√ 安全报告"],
        ["成本", "低", "中", "高【填：调研价格】", "约 350 元/套"]]
table(sl, 0.7, 1.9, 11.9, rows, [2.2, 2.0, 2.2, 2.9, 2.6], size=14, row_h=0.62, highlight_col=4)
text(sl, 0.7, 6.4, 11.9, 0.4, "注：竞品价格以团队市场调研为准，答辩前补齐", size=11, color=GREY)
notes(sl, "和现有方案对比：爆闪灯不感知来车，入侵报警器车辆闯入后才报警，智慧作业区系统功能强但贵、需要专业安装。我们在保留感知、分级、提醒工人、数据记录能力的同时，做到了即放即用、约350元一套。")

sl = content_slide(4, "县乡道路小型养护市场广阔", "数据来源：交通运输部《2024年交通运输行业发展统计公报》")
big_number(sl, 0.5, 1.95, 3.15, "549.04", "万公里", "全国公路里程", NAVY, nsize=38)
big_number(sl, 3.7, 1.95, 3.15, "464.37", "万公里", "农村公路里程", ORANGE, nsize=38)
big_number(sl, 6.9, 1.95, 3.1, "19.07", "万公里", "高速公路里程", CYAN, nsize=38)
card(sl, 10.1, 1.95, 2.8, 2.0, "政策契合", "交通强国建设纲要\n公路数字化转型意见\n安全生产治本攻坚", color=RED, head_size=15, body_size=11.5)
models = [("智能锥桶套装", "哨兵+联动+工人端+网关"), ("灯头改装套件", "装在现有锥桶上"), ("安全数据平台", "按年订阅，出安全台账")]
for i, (h_, b_) in enumerate(models):
    x = 0.6 + i * 4.1
    s = rect(sl, x, 4.45, 3.85, 1.55, NAVY if i != 1 else CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(sl, x, 4.6, 3.85, 0.55, h_, size=19, color=WHITE, bold=True, align="c")
    text(sl, x, 5.2, 3.85, 0.6, b_, size=13, color=WHITE, align="c")
text(sl, 0.6, 6.25, 12.2, 0.45, "目标客户：公路养护公司 · 市政养护单位 · 高速运营公司 · 交警路政 · 占道施工单位", size=14, color=NAVY, bold=True)
notes(sl, "市场方面，全国公路里程549.04万公里，其中农村公路464.37万公里，县乡道路日常养护点多量大。现有智慧作业区产品主要面向高速公路，县乡道路应用很少。我们规划三种推广模式：整套销售、灯头改装套件和数据平台订阅。产品契合交通强国、公路数字化转型和安全生产治本攻坚等政策方向。")

# ================================================================== 18 团队
section_slide(5, "团队与成果", "交通 + 电子 + 计算机 + 设计 交叉团队")
sl = content_slide(5, "跨学科团队 分工明确", "")
team = [("负责人", "交通工程", "需求调研 · 预警算法\n测试方案 · 申报书"), ("成员", "电子信息", "硬件选型 · 电路 PCB\n电源 · 固件"),
        ("成员", "计算机", "ESP-NOW 组网\n云平台开发"), ("成员", "设计/经管", "外壳结构 · 市场调研\n答辩与视频")]
for i, (r_, m_, d_) in enumerate(team):
    x = 0.6 + i * 3.1
    rect(sl, x, 1.9, 2.85, 2.9, BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    av = rect(sl, x + 0.92, 2.1, 1.0, 1.0, LIGHT, shape=MSO_SHAPE.OVAL)
    text(sl, x + 0.92, 2.42, 1.0, 0.4, "照片", size=11, color=GREY, align="c")
    text(sl, x, 3.2, 2.85, 0.4, f"【填】  {r_}", size=14, color=NAVY, bold=True, align="c")
    text(sl, x, 3.6, 2.85, 0.35, m_, size=12, color=ORANGE, bold=True, align="c")
    text(sl, x + 0.1, 3.98, 2.65, 0.8, d_, size=11.5, color=INK, align="c")
res = [("实物样机", "≥3 锥桶 + 工人端 + 网关"), ("软件平台", "看板 + 事件库 + 安全报告"), ("完整代码", "固件 / 平台 / 工具 已完成"),
       ("知识产权", "实用新型 1 项 · 软著 1 项【填：申请号】")]
for i, (h_, b_) in enumerate(res):
    x = 0.6 + i * 3.1
    s = rect(sl, x, 5.15, 2.85, 1.55, NAVY if i % 2 == 0 else CYAN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    text(sl, x, 5.25, 2.85, 0.5, h_, size=17, color=WHITE, bold=True, align="c")
    text(sl, x + 0.1, 5.78, 2.65, 0.8, b_, size=11.5, color=WHITE, align="c")
notes(sl, "我们是交通、电子、计算机、设计的交叉团队，分工如图。目前完成了全部固件、平台和工具代码，正在制作实物样机，并计划申请实用新型专利和软件著作权各一项。")

# ================================================================== 20 结束
sl = prs.slides.add_slide(BLANK); state["page"] += 1
pic(sl, IMG + "hero_cone.png", 0, 0, crop_to=(W, H))
ov = rect(sl, 0, 0, W, H, NAVY2)
sp = ov.fill._xPr.find(qn("a:solidFill"))[0]; sp.append(sp.makeelement(qn("a:alpha"), {"val": "78000"}))
text(sl, 0, 2.3, W, 1.2, "让每一个锥桶都能“看见”危险", size=44, color=WHITE, bold=True, align="c")
rect(sl, W / 2 - 0.8, 3.65, 1.6, 0.07, ORANGE)
text(sl, 0, 3.95, W, 0.7, "守护每一位养护工人平安回家", size=22, color=CYAN, align="c", bold=True)
text(sl, 0, 5.3, W, 0.6, "恳请各位评委老师批评指正", size=20, color=WHITE, align="c")
notes(sl, "我们希望让每一个锥桶都能看见危险，守护每一位养护工人平安回家。汇报完毕，恳请各位评委老师批评指正。")

out = "./哨兵_挑战杯答辩PPT.pptx"
prs.save(out)
print(out, state["page"])
