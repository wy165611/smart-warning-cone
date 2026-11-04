# -*- coding: utf-8 -*-
"""生成第二十届“挑战杯”（大挑）科技发明制作类作品申报书与研究报告（docx）。

在本目录运行：python gen_docx.py（先运行 figs.py 生成 img/ 下的图）。
文中数字须与仓库代码、docs/项目说明书.md 一致；没有出处的内容用【待补充】标出。
"""
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

IMG = "img/"

PH = re.compile(r"(【(?:填|待补充|待实测|待实机核对|请核对)[^】]*】)")

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.6)
sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.3)

# ---------- 样式 ----------
def set_font(run, east="宋体", west="Times New Roman", size=12, bold=False, color=None):
    run.font.name = west
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east)
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)

st = doc.styles["Normal"]
st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_after = Pt(0)


def add_runs(p, text, east="宋体", size=12, bold=False, color=None):
    """支持 **加粗** 和 【填】高亮"""
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        b = bold
        if part.startswith("**") and part.endswith("**"):
            part = part[2:-2]; b = True
        for seg in PH.split(part):
            if not seg:
                continue
            r = p.add_run(seg)
            set_font(r, east=east, size=size, bold=b, color=color)
            if PH.fullmatch(seg):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def para(text, indent=True, size=12, align=None, bold=False, east="宋体", space_after=0, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "r":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_after = Pt(space_after)
    add_runs(p, text, east=east, size=size, bold=bold, color=color)
    return p


def heading(text, level=1):
    sizes = {0: 16, 1: 15, 2: 14, 3: 12}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12 if level <= 1 else 6)
    p.paragraph_format.space_after = Pt(6 if level <= 1 else 3)
    p.paragraph_format.keep_with_next = True
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_font(r, east="黑体", size=sizes[level], bold=True)
    # 让导航窗格识别
    if level >= 1:
        pPr = p._p.get_or_add_pPr()
        ol = OxmlElement("w:outlineLvl"); ol.set(qn("w:val"), str(level - 1)); pPr.append(ol)
    return p


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def shade(cell, color="D9E2F3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def cell_text(cell, text, size=10.5, bold=False, align="l", east="宋体"):
    cell.text = ""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.first_line_indent = Pt(0)
        p.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "j": WD_ALIGN_PARAGRAPH.JUSTIFY}[align]
        add_runs(p, line, east=east, size=size, bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER



def fix_widths(t, widths):
    """固定列宽（Word 与 WPS/LibreOffice 均生效）"""
    t.autofit = False
    tbl = t._tbl; tblPr = tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(int(sum(widths) * 567))); tw.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")): tblPr.remove(old)
    tblPr.append(tw)
    grid = tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 567)))
    for row in t.rows:
        for j, w in enumerate(widths[:len(row.cells)]):
            row.cells[j].width = Cm(w)

def table(rows, widths=None, header=True, size=10.5, align_body="c"):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            if header and i == 0:
                cell_text(c, val, size=size, bold=True, align="c", east="黑体"); shade(c)
            else:
                cell_text(c, val, size=size, align=align_body if j > 0 or align_body == "c" else "l")
    if widths:
        fix_widths(t, widths)
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        if header and i == 0:
            th = OxmlElement("w:tblHeader"); trPr.append(th)
    spacer()
    return t


def spacer():
    sp = doc.add_paragraph(); sp.paragraph_format.line_spacing = 1.0
    sp.paragraph_format.space_after = Pt(0)
    r = sp.add_run(" "); r.font.size = Pt(6)


def caption(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    add_runs(p, text, east="黑体", size=10.5)


def table_caption(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    add_runs(p, text, east="黑体", size=10.5)


def figure(path, width_cm, cap):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width_cm))
    caption(cap)


def formula(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); set_font(r, east="宋体", west="Cambria Math", size=12)


def add_page_number(section):
    footer = section.footer; p = footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)
        set_font(r, size=10.5)

# =====================================================================
# 共享事实
# =====================================================================
from facts import (  # noqa: E402
    CATEGORY, COMPETITION, CONFIRM, CORE, COST_FOLLOWER, COST_GATEWAY, COST_KIT, COST_SENTINEL,
    COST_WORKER, COUNTY_KM, EXPRESSWAY_KM, FHWA_2023_DEATHS, FHWA_2024_DEATHS, FLASH_DETAIL, FLASH_USE,
    FQBN, RAM_DETAIL, RAM_USE,
    LINK_TIMEOUT_S, MAX_HOPS, NIGHT, OVERSPEED, RAIN, REFS, RELEASE_S, REPEAT_MS, ROAD_KM, RURAL_KM,
    SCHOOL, SPEED_LIMIT, TESTS, TITLE, TOWNSHIP_KM, TTC1, TTC2, VILLAGE_KM, ref_no,
    CN_CASE_BLURB, CN_CASE_NOTE,
)

R = lambda key: f"[{ref_no(key)}]"  # noqa: E731
SCHOOL_NAME = SCHOOL.split()[0]

# =====================================================================
# 封面
# =====================================================================
for _ in range(2):
    doc.add_paragraph()
para(COMPETITION, indent=False, align="c", size=16, east="黑体", bold=True)
doc.add_paragraph()
para("作 品 申 报 书", indent=False, align="c", size=36, east="黑体", bold=True)
for _ in range(3):
    doc.add_paragraph()
cover = [
    ("作品名称：", TITLE),
    ("学校全称：", f"{SCHOOL_NAME}【请核对】"),
    ("申报者姓名\n（集体名称）：", "【填：集体作品写团队名称，如“哨兵”团队】"),
    ("类    别：", "□ 自然科学类学术论文\n□ 哲学社会科学类社会调查报告\n□ 科技发明制作 A 类\n■ 科技发明制作 B 类"),
]
t = doc.add_table(rows=len(cover), cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, (k, v) in enumerate(cover):
    cell_text(t.cell(i, 0), k, size=14, bold=True, east="黑体", align="l")
    cell_text(t.cell(i, 1), v, size=14, align="l")
fix_widths(t, [4.4, 10.8])
for _ in range(4):
    doc.add_paragraph()
para("【填：申报日期】", indent=False, align="c", size=14)
para("说明：科技发明制作 B 类指投入较少、为生产技术或社会生活带来便利的小发明、小制作；A 类指科技含量较高、制作投入较大的作品。本作品物料投入较少，建议申报 B 类，最终以学校评审意见为准。", indent=False, size=10.5, color="666666")
page_break()

# =====================================================================
# 填写说明
# =====================================================================
heading("说  明", 0)
for n in [
    "1．本文件依据往届“挑战杯”作品申报书的通行栏目整理，正式提交时请以第二十届组委会和学校下发的模板为准，逐栏誊入。",
    "2．科技发明制作类作品填写 A（申报者情况）、B3（申报作品情况）和 C（推荐者情况）部分，并附研究报告（本文件附件）。",
    "3．参赛资格、作者人数、指导教师人数和时间节点以本届及学校通知为准（各校通知中参赛对象截止时间为 2027 年 6 月 1 日）。",
    "4．黄色底纹的【填】【待补充】【请核对】处必须由申报者据实填写；没有材料的栏目写“暂无”，不要估填。提交前删除全部底纹。",
    "5．文中技术参数与仓库 github.com/wy165611/smart-warning-cone 中的代码一致；外部数字均附可打开的出处，见研究报告“参考文献”。",
]:
    para(n, indent=False)
page_break()

# =====================================================================
# A. 申报者情况
# =====================================================================
heading("A. 申报者情况（集体作品）", 1)
para("说明：1．由申报者本人按要求填写；2．申报者代表为作者中学历最高者，其余作者按学历高低排列；3．学籍管理部门签章视为对申报者情况的确认。", indent=False, size=10.5)
rows = [["", "姓名", "性别", "年龄", "学历", "所在单位（学院/专业/年级）", "分工"]]
roles = ["负责人：需求调研、预警算法、测试方案、申报书", "硬件选型、电路与 PCB、电源、固件", "ESP-NOW 组网、平台开发", "外壳结构、市场调研、答辩与视频"]
for i, r in enumerate(roles):
    rows.append(["申报者代表" if i == 0 else f"其他作者{i}", "【填】", "", "", "【填】", "【填】", r])
table(rows, widths=[1.8, 1.6, 1.3, 1.3, 1.1, 3.9, 4.8], size=9.5)
rows = [["项目", "内容"],
        ["申报者代表通讯地址", "【填：学校地址、邮编】"],
        ["联系电话 / 电子邮箱", "【填】"],
        ["指导教师", "【填：姓名、职称、所在单位】"],
        ["资格认定（学籍管理部门意见）", "以上作者是否为 2027 年 6 月 1 日前正式注册在校的全日制非成人教育、非在职的高等学校中国籍本科生或研究生。\n是 □    否 □\n\n（学籍管理部门签章）            年    月    日"],
        ["资格认定（院、系、所或年级意见）", "本作品是否为课外学术科技或社会实践活动成果。\n是 □    否 □\n负责人签名：                      年    月    日"]]
table(rows, widths=[4.4, 11.4], size=10.5, align_body="l")
para("注：作者超过 3 人或无法区分第一作者的须申报集体作品；分工一栏为示例，请按实际修改。", indent=False, size=10.5, color="666666")

heading("申报者声明", 2)
para("我（们）郑重声明：所提交的作品为本人（团队）在指导教师指导下独立完成的课外学术科技成果，作品中引用他人成果之处均已注明出处；作品未以同一内容参加过“挑战杯”系列竞赛及其他全国性竞赛评奖；如有违反，愿承担一切后果。")
para("申报者代表签名：                    日期：      年    月    日", indent=False, align="r")
page_break()

# =====================================================================
# B3. 申报作品情况（科技发明制作）
# =====================================================================
heading("B3. 申报作品情况（科技发明制作）", 1)
para("说明：1．由申报者本人填写；2．科研管理部门签章视为对所填内容的确认；3．本表附研究报告，提供图表、曲线、试验数据、原理结构图、外观图（照片）；4．作品分类按发明点或创新点所在类别填报。", indent=False, size=10.5)

b3_purpose = f"""**一、目的**
公路养护常在不中断交通的条件下进行，作业人员面向路面、背对来车，现场噪声大；锥桶、标志等设施能隔离和告知，却无法判断某一辆车是否正在快速接近。美国联邦公路局（FHWA）2026 年发布的资料显示，2024 年美国工作区交通事故死亡 {FHWA_2024_DEATHS} 人，超过一半的致死事故发生在夜间，追尾占致死事故的近四分之一{R("HOP-26-060")}；这些是美国数据，只说明作业区遭来车撞击是被持续统计的风险。国内可引用的典型案例：{CN_CASE_BLURB}{R("1·7")}。{CN_CASE_NOTE}全国养护作业区伤亡汇总表仍【待补充：数据来源】。截至 2025 年末，我国公路里程 {ROAD_KM} 万公里，其中农村公路 {RURAL_KM} 万公里{R("2025年")}，日常小修保养点多面广，通常只摆放锥桶和标志。本作品在不替代 JTG H30—2015 和 GB 5768.4—2017 所要求设施的前提下{R("2015年第16号")}{R("GB 5768.4")}，给普通锥桶增加一层低成本的主动提醒：测到来车、算出碰撞时间、按危险程度分级提醒司机和工人，并记录每一次接近。
**二、基本思路**
作业区上游的“哨兵锥桶”用 24 GHz 毫米波雷达测量来车距离和速度，经卡尔曼滤波后计算碰撞时间（TTC），按 TTC 与超速双判据分为安全、一级、二级；联动锥桶通过 ESP-NOW 接收预警并按编号错相点亮，形成指向变道方向的流水灯；工人报警器在二级预警时震动并蜂鸣；离线语音完成开始作业、封道方向和雨天/夜间模式切换；网关把预警与“接近事件”转为 MQTT，平台生成安全报告。全部判定在锥桶本地完成，网关和平台断开时预警仍然工作。
**三、创新点（设计特点）**
1．按危险程度提醒：TTC 与超速双判据分级，平时慢闪，危险时才升级；
2．一次判定同时提醒司机和工人：灯光与穿戴端使用同一等级；
3．锥桶之间无基础设施组网：ESP-NOW 广播、序号去重、预警包最多 2 跳中继，模式配置包也会转发；
4．环境系数一键切换：雨天 ×{RAIN}、夜间 ×{NIGHT}，可叠加，语音切换；
5．接近事件结构化记录：最高等级、最高车速、最小 TTC、最近距离、持续时间。
以上为设计特点，效果需封闭场地对比试验验证。
**四、技术关键**
1．LD2451 串口帧解析与多目标中“最危险目标”选择；2．一维卡尔曼滤波抑制单帧跳变；3．连续 {CONFIRM} 帧确认升级、目标消失 {RELEASE_S} s 按时间解除（雷达掉线也能解除）；4．广播组网的序号去重、随机退避与重启兼容；5．户外供电（雷达 5 V、供电能力 >200 mA）与防水结构。
**五、主要技术指标（设计值，实测见研究报告第 7 章）**
探测距离 ≤100 m、水平 ±15°、垂直 ±7°（厂家指标，未复测）{R("使用手册")}；一级 TTC < {TTC1:g} s 或车速 > {SPEED_LIMIT} km/h × {OVERSPEED}，二级 TTC < {TTC2:g} s；预警期间每 {REPEAT_MS} ms 重发，中继 ≤{MAX_HOPS} 跳；物料估算：哨兵约 {COST_SENTINEL} 元，演示套装（1 哨兵 + 2 联动 + 1 工人端 + 1 网关 + 辅料）约 {COST_KIT} 元。"""

b3_sci = f"""**1．科学性**
（1）判据有出处：TTC 以“保持当前速度与路径时距离碰撞还剩多少时间”衡量危险程度，由 Hayward（1972）作为交通冲突的危险尺度提出{R("Hayward")}；本作品取 TTC = d /(v/3.6)。5 s、2.5 s 是设计初值，尚未标定。
（2）测量手段适合户外：LD2451 为 24 GHz FMCW 雷达，厂家定位为室外车辆状态检测，输出距离、速度、方向和角度{R("使用手册")}。
（3）信号处理成熟：一维常值卡尔曼滤波{R("Kalman")}，计算量小，可在 ESP32-C3 上逐帧运行。
（4）工程实现（2026-11-03）：四个固件在 {CORE}（{FQBN}）下编译通过、无警告；程序空间 {FLASH_USE}，动态内存 {RAM_USE}。Python 参考实现 {TESTS} 项单元测试通过。本机 Mosquitto + 平台 + 模拟器端到端跑通，看板数据来自模拟器，不是路试。尚未烧录，也没有外场测试。
**2．先进性（功能定位对比，非产品测评）**
| 现有方式 | 局限（功能层面） | 本作品 |
| 锥桶、水马、标志 | 隔离和告知，不感知来车 | 增加雷达感知与分级提醒，不替换原设施 |
| 定频爆闪灯 | 不区分危险程度 | 平时慢闪，危险时升级并联动流水灯 |
| 闯入式报警（压感管、红外对射等） | 车辆越过检测线后才报警 | 车辆在雷达范围内即按 TTC 提前分级 |
| 带情报板和平台的大型系统 | 设备多、部署重 | 节点即放即用，网关和平台可选 |
| 防撞缓冲车 | 减轻后果 | 事前提醒，可互补 |
FHWA 夜间作业区专题已推广顺序警示灯和自动入侵报警{R("EDC-8")}，23 CFR 630.1108 也把入侵报警列为可选措施{R("630.1108")}。本作品的特点在于把 TTC 提前分级、流水灯、工人穿戴端和事件记录集成在一个低成本节点中。【待补充：国内文献与在售产品的名称、参数、价格及出处】
参考文献：见研究报告。"""

b3_use = f"""**一、使用说明**
1．布设：按 JTG H30—2015 和 GB 5768.4—2017 设置作业区后，把哨兵锥桶放在作业区上游、雷达朝来车（建议 50–150 m，按限速与视距现场确定）；联动锥桶沿过渡段摆放，编号从哨兵往作业区递增；工人佩戴报警器；网关放在作业车上。
2．启动：说“小哨兵”唤醒，再说“开始作业”；按需说“左侧封道/右侧封道”“雨天模式”“夜间模式”。
3．运行：安全时黄灯慢闪；一级红黄快闪、联动锥桶流水灯；二级红色爆闪 + 蜂鸣，工人报警器震动。
4．收工：说“结束作业”，平台可导出当日安全报告。
**二、技术特点**
物料投入低（哨兵估算约 {COST_SENTINEL} 元）；卡装在普通锥桶顶部，不需布线；判定在本地完成，网络中断不影响预警；节点数量按作业区长度增减。
**三、适用范围**
占一条车道、当天收工的小修保养；县乡公路和城市道路的日常修补；事故现场临时管控。不适用于替代防撞缓冲车，未标定前不作测速执法依据。
**四、推广前景**
我国农村公路 {RURAL_KM} 万公里（县道 {COUNTY_KM}、乡道 {TOWNSHIP_KM}、村道 {VILLAGE_KM} 万公里）{R("2025年")}，日常养护作业分散；里程只说明养护面广，不等于设备需求量。作品方向与《交通强国建设纲要》{R("交通强国")}、交公路发〔2023〕131 号文“鼓励精准化、低成本的路网监测感知和路侧信息发布装备”{R("131")}以及安全生产治本攻坚三年行动中的“技防”措施{R("治本攻坚")}相契合。可能的推广形式：整套锥桶、灯头改装模块、数据平台服务。
**五、经济效益**
【待补充：走访 2～3 家养护单位，记录作业频次、现有设施、采购意愿和可接受价格；完成量产成本估算后再测算】在此之前不填写市场规模和销售额。"""

rows = [
    ["作品全称", TITLE],
    ["作品分类", "（ A ）A．机械与控制（包括机械、仪器仪表、自动化控制、工程、交通、建筑等）\n         B．信息技术（包括计算机、电信、通讯、电子等）\n         C．数理  D．生命科学  E．能源化工\n注：发明点在交通安全与自动预警，建议选 A；若学校按电子信息归口，可改选 B。"],
    ["作品设计、发明的目的和基本思路，创新点，技术关键和主要技术指标", b3_purpose],
    ["作品的科学性、先进性（必须说明与现有技术相比、该作品是否具有突出的实质性技术特点和显著进步。请提供技术性分析说明和参考文献资料）", b3_sci],
    ["作品在何时、何地、何种机构举行的评审、鉴定、评比、展示等活动中获奖及鉴定结果", "【填：如校赛获奖情况；无则填“无”】"],
    ["作品所处阶段", f"（ A ）A．实验室阶段  B．中试阶段  C．生产阶段  D．（自填）\n说明：已完成系统方案、四类节点固件与平台软件；固件编译通过（{CORE}），单元测试与平台端到端联调通过。【待补充：实物样机完成情况与封闭场地测试情况】"],
    ["技术转让方式", "【填：如“暂无”】"],
    ["作品可展示的形式", "□ 实物、产品  □ 模型  ■ 图纸  □ 磁盘\n■ 现场演示  ■ 图片  □ 录像  □ 样品\n注：实物样机和录像完成后再勾选。"],
    ["使用说明及该作品的技术特点和优势，提供该作品的适应范围及推广前景的技术性说明及市场分析和经济效益预测", b3_use],
    ["专利申请情况", "□ 提出专利申请    申请号：【填】    申请日期：【填】\n□ 已获专利权批准  批准号：【填】    批准日期：【填】\n□ 未提出专利申请\n注：按实际勾选，未申请就勾“未提出专利申请”。"],
]
t = doc.add_table(rows=len(rows), cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER


def fill_rich(cell, text, size=10):
    """单元格内容：以 | 开头的连续行渲染为嵌套表"""
    cell.text = ""
    first = True
    lines = text.split("\n"); i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            nt = cell.add_table(rows=len(block), cols=len(block[0])); nt.style = "Table Grid"
            for r, row in enumerate(block):
                for c, v in enumerate(row):
                    cell_text(nt.cell(r, c), v, size=9.5, bold=(r == 0), align="c" if r == 0 else "l", east="黑体" if r == 0 else "宋体")
                    if r == 0:
                        shade(nt.cell(r, c))
            fix_widths(nt, [3.4, 4.2, 4.3])
            cell.add_paragraph()
            first = False
            continue
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.line_spacing = 1.2
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, line, size=size)
        i += 1


for i, (k, v) in enumerate(rows):
    cell_text(t.cell(i, 0), k, size=10.5, bold=True, align="c", east="黑体"); shade(t.cell(i, 0))
    fill_rich(t.cell(i, 1), v)
fix_widths(t, [3.2, 12.6])
doc.add_paragraph()
para("科研管理部门签章：                                    年    月    日", indent=False, align="r")
page_break()

# =====================================================================
# C. 推荐者情况
# =====================================================================
heading("C. 推荐者情况及对作品的说明", 1)
para("说明：1．由推荐者本人填写；2．推荐者须具有高级专业技术职称，并是与申报作品相同或相关领域的专家学者或专业技术人员；3．推荐者填写此部分，即视为同意推荐；4．推荐者所在单位签章仅视为对推荐者身份的确认。", indent=False, size=10.5)
for n in (1, 2):
    rows = [["推荐者情况", "姓名：【填】  性别：【填】  年龄：【填】  职称：【填】\n工作单位：【填】\n通讯地址：【填】    邮编：【填】    电话：【填】"],
            ["推荐者所在单位签章", "\n（签章）                    年    月    日"],
            ["请对申报者申报情况的真实性作出阐述", "【填：由推荐者本人撰写】"],
            ["请对作品的意义、技术水平、适用范围及推广前景作出您的评价", "【填：由推荐者本人撰写】"],
            ["其他说明", "【填：无则写“无”】"]]
    table_caption(f"推荐者 {n}")
    t = doc.add_table(rows=len(rows), cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(rows):
        cell_text(t.cell(i, 0), k, bold=True, align="c", east="黑体"); shade(t.cell(i, 0)); cell_text(t.cell(i, 1), v, align="l")
    fix_widths(t, [4.2, 11.6])
    doc.add_paragraph()

# =====================================================================
# 附件：研究报告
# =====================================================================
new = doc.add_section(WD_SECTION.NEW_PAGE)
new.footer.is_linked_to_previous = False
pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1"); new._sectPr.append(pg)
add_page_number(new)
heading("附件  作品研究报告（科技发明制作说明书）", 0)
para(TITLE, indent=False, align="c", size=14, east="黑体", bold=True, space_after=6)

heading("摘  要", 2)
para(f"公路养护作业区的锥桶、标志等设施能隔离和告知，但无法感知某一辆车是否正在快速接近。本作品设计了智能预警锥桶系统“哨兵”：上游哨兵锥桶以 24 GHz 毫米波雷达测量来车距离与速度，经一维卡尔曼滤波后计算碰撞时间（TTC），按 TTC 与超速双判据分为三级，并可按雨天、夜间切换阈值系数；联动锥桶通过 ESP-NOW 广播组网形成流水灯；工人报警器在二级预警时震动提醒；离线语音支持一句话部署；网关把预警与接近事件上传平台并生成安全报告。2026-11-03，四类节点固件在 {CORE} 下编译通过（程序空间 {FLASH_USE}，动态内存 {RAM_USE}），Python 参考实现 {TESTS} 项单元测试通过，并用本机 Mosquitto 与模拟器跑通平台。理论计算表明，在 {SPEED_LIMIT} km/h 时，雷达 100 m 标称探测距离对应约 9.0 s 的时间窗口。实物样机与封闭场地测试尚在进行，阈值需按实测标定。哨兵节点物料估算约 {COST_SENTINEL} 元。")
para("**关键词**：公路养护；作业区安全；毫米波雷达；碰撞时间；ESP-NOW；协同预警", indent=False)

heading("1  研究背景与意义", 1)
heading("1.1  作业区安全问题", 2)
para(f"养护作业通常“边通车、边施工”。作业人员面向路面、背对来车，往往在车辆已经很近时才察觉危险；司机则可能因超速、分心或夜间视距不足而未及时发现作业区。FHWA 2026 年发布的资料显示：2024 年美国工作区交通事故死亡 {FHWA_2024_DEATHS} 人（2023 年为 {FHWA_2023_DEATHS} 人），超过一半的致死事故发生在夜间，追尾占近四分之一，超速是三分之一以上致死事故的因素{R('HOP-26-060')}。这些是美国统计，不能直接代表我国情况。国内可引用的典型案例：{CN_CASE_BLURB}{R("1·7")}。{CN_CASE_NOTE}全国养护作业区伤亡汇总表仍【待补充：数据来源】。")
figure(IMG + "workzone.png", 14.5, "图 1  养护作业区示意（AI 生成的概念图，正式稿请替换为团队实拍照片）")
heading("1.2  现有设施的功能局限", 2)
for s in ["（1）被动：锥桶、水马、标志牌只能隔离和告知，不能判断某辆车是否超速或正在快速接近。",
          "（2）同质：定频爆闪灯不区分危险程度。",
          "（3）滞后：压感管、红外对射一类闯入式报警在车辆越过检测线后才报警，提前量取决于检测线的位置，而不是这辆车当前的速度。",
          "（4）偏重：带情报板和平台的大型系统设备多、部署重，小型养护不一定搬得动。",
          "（5）缺数据：一次危险接近如果没有被记录，就无法用于标定和管理改进。",
          "以上是功能分类，不是对具体产品的测评。"]:
    para(s)
heading("1.3  政策与标准依据", 2)
para(f"JTG H30—2015《公路养护安全作业规程》自 2015 年 6 月 1 日起施行{R('2015年第16号')}，GB 5768.4—2017 规定了作业区的标志和标线{R('GB 5768.4')}。本作品是这些设施之上的补充，不替代其中任何一项。交公路发〔2023〕131 号文鼓励精准化、低成本的路网监测感知和路侧信息发布装备{R('131')}；安全生产治本攻坚三年行动强调“人防、技防、工程防、管理防”措施落地{R('治本攻坚')}。截至 2025 年末，我国公路里程 {ROAD_KM} 万公里，其中农村公路 {RURAL_KM} 万公里{R('2025年')}。")

heading("2  国内外研究与实践现状", 1)
para(f"美国 23 CFR 630.1108 把入侵报警、速度管理和智能交通系统列为工作区“其他交通控制措施”，并说明执法车辆不能代替临时交通控制设施{R('630.1108')}。Gambatese 等（2017）为俄勒冈州交通厅评估了作业区入侵报警技术，指出既往研究结论不一、应用有限，在受控条件和实际作业区的有限样本测试中，视觉、声音和触觉报警都可能有效{R('32574')}。FHWA 夜间作业区专题把自动入侵报警、顺序点亮的警示灯列为推广策略，并提到有州交通厅评估装在防撞缓冲车上、车辆接近时自动鸣笛亮灯的系统{R('EDC-8')}。")
para("由此可见，“来车接近时自动报警”和“顺序警示灯引导并道”在国外都有实践，本作品不是这些方向的首创。本作品的特点是把 TTC 提前分级、流水灯、工人穿戴端提醒和事件记录集成在一个低成本节点中。【待补充：国内相关论文、学位论文和在售产品，逐条打开原文后按 GB/T 7714 著录】")
table_caption("表 1  现有作业区安全设施的功能定位")
table([["类型", "典型形式", "局限（功能层面）", "本作品的做法"],
       ["传统设施", "锥桶、水马、标志牌", "隔离和告知，不感知来车", "加装雷达灯头，主动感知"],
       ["定频警示灯", "太阳能爆闪灯", "不区分危险程度", "分级灯光 + 流水灯"],
       ["闯入式报警", "压感管、红外对射", "越线后才报警", "按 TTC 提前分级"],
       ["大型系统", "雷达 + 情报板 + 平台", "设备多、部署重", "节点即放即用"],
       ["防撞缓冲车", "车载吸能装置", "减轻后果", "事前提醒，可互补"]],
      widths=[2.4, 3.6, 4.8, 5.0], size=10)

heading("3  系统总体设计", 1)
heading("3.1  设计目标", 2)
para("（1）提前：在车辆到达作业区前留出减速、变道和避让的时间；（2）分级：只在危险时强提醒；（3）可靠：本地判定、离线可用、防误报；（4）易部署：不改造现有锥桶；（5）可追溯：记录接近事件。")
heading("3.2  系统架构", 2)
para("系统由感知层、边缘决策与组网层、平台层组成（图 2）。哨兵锥桶负责感知与判定；联动锥桶和工人报警器执行预警；网关把 ESP-NOW 报文转换为 MQTT；平台负责存储、展示与报告。")
figure(IMG + "arch.png", 15.5, "图 2  系统总体架构")
heading("3.3  现场布设", 2)
para("哨兵锥桶放在作业区上游，雷达朝来车（建议 50–150 m，按限速与视距现场确定）；联动锥桶沿过渡段布设，编号由近及远递增，依次点亮形成流水灯；工人佩戴报警器；网关放在作业车上（图 3）。")
figure(IMG + "layout.png", 15.5, "图 3  作业区布设俯视示意（示意，不按比例）")

heading("4  硬件设计", 1)
figure(IMG + "hw.png", 13.5, "图 4  哨兵锥桶硬件框图")
table_caption("表 2  哨兵锥桶主要器件")
table([["模块", "型号/方案", "关键参数", "选型理由"],
       ["主控", "ESP32-C3", "RISC-V，Wi-Fi，ESP-NOW", "一颗芯片完成判定与组网"],
       ["雷达", "HLK-LD2451", "24–24.25 GHz FMCW，≤100 m，±15°/±7°，5 V/>200 mA", "厂家定位为室外车辆检测"],
       ["灯光", "WS2812B 灯带 30 灯", "可编程 RGB，GPIO10", "分级闪烁与流水灯"],
       ["声音", "有源蜂鸣器 + AO3400", "MOSFET 低边驱动，GPIO3", "二级预警声报警"],
       ["语音", "ASRPRO", "离线识别，UART0 9600（GPIO20/21）", "不用掏手机即可切换模式"],
       ["电源", "18650 + TP4056 + 5 V 升压", "雷达需 5 V；电池分压接 GPIO0", "野外独立供电"],
       ["结构", "3D 打印灯头", "PETG，雷达窗口无金属", "不改造现有锥桶"]],
      widths=[1.6, 3.6, 5.8, 4.8], size=9.5)
para("雷达占用 UART1（GPIO6/7），ASRPRO 占用 UART0，日志走 USB（需开启 USB CDC On Boot）。联动锥桶去掉雷达与语音模块；工人报警器采用 ESP32-C3、扁平振动马达（GPIO4）、蜂鸣器（GPIO3）、LED（GPIO5）和按键（GPIO1）；网关为 USB 供电的 ESP32 开发板。")
table_caption("表 3  演示套装物料估算（网店常见价，非报价）")
table([["组成", "数量", "单价（元，约）", "小计（元，约）"],
       ["哨兵锥桶模块", "1", str(COST_SENTINEL), str(COST_SENTINEL)],
       ["联动锥桶模块", "2", str(COST_FOLLOWER), str(COST_FOLLOWER * 2)],
       ["工人报警器", "1", str(COST_WORKER), str(COST_WORKER)],
       ["网关", "1", str(COST_GATEWAY), str(COST_GATEWAY)],
       ["锥桶、外壳、辅料", "—", "—", "100"],
       ["合计", "", "", f"≈{COST_KIT}"]], widths=[5.3, 2.5, 4.0, 4.0], size=10)

heading("5  核心算法", 1)
figure(IMG + "flow.png", 15.5, "图 5  哨兵锥桶预警判定流程")
heading("5.1  雷达数据解析与目标筛选", 2)
para(f"LD2451 串口为 115200 bps、8N1，帧头 F4 F3 F2 F1、帧尾 F8 F7 F6 F5，每个目标 5 字节（角度、距离、方向、速度、信噪比）；有目标时约 100 ms 一帧，无目标约 1 s 一帧{R('使用手册')}{R('串口通信协议')}。方向按协议表 9 取 0x01 为靠近；该文档示例文字与表 9 不一致，【待实机核对】。程序只保留靠近、速度 ≥5 km/h、距离 ≤100 m 的目标，并选 TTC 最小者。")
heading("5.2  卡尔曼滤波", 2)
para(f"对距离和速度分别采用一维常值模型{R('Kalman')}：")
formula("P⁻ = P + Q，   K = P⁻ /(P⁻ + R)，   x = x + K(z − x)，   P = (1 − K)P⁻")
para("Q = 0.5、R = 4 为初始参数，可用实测数据离线调整。")
heading("5.3  碰撞时间与三级预警", 2)
para(f"TTC 表示车辆保持当前速度到达哨兵位置所需的时间{R('Hayward')}：")
formula("TTC = d / (v / 3.6)        （d：m；v：km/h；TTC：s）")
para("速度不超过 1 km/h 时取 99 s，避免除零。预警等级见表 4，判定区域见图 6。比较均为“严格小于”，TTC 恰为 2.5 s 时属于一级。")
table_caption("表 4  预警分级规则（config.h 默认值，未标定）")
table([["等级", "触发条件", "哨兵 / 联动锥桶", "工人报警器"],
       ["安全", f"无目标，或 TTC ≥ {TTC1:g} s 且未超速", "黄灯慢闪", "静默"],
       ["一级", f"TTC < {TTC1:g} s，或车速 > {SPEED_LIMIT} × {OVERSPEED} km/h", "红黄快闪 + 流水灯", "每 1.5 s 短震 + LED"],
       ["二级", f"TTC < {TTC2:g} s", "红色爆闪 + 蜂鸣", "连续震动 + 蜂鸣（按键静音 10 s，震动不停）"]],
      widths=[1.6, 5.4, 4.2, 4.6], size=10)
figure(IMG + "ttc_map.png", 12.5, f"图 6  基于 TTC 的三级预警判定区域（限速 {SPEED_LIMIT} km/h）")
heading("5.4  环境系数", 2)
para(f"雨天模式把两档 TTC 阈值乘以 {RAIN}，夜间模式乘以 {NIGHT}，可叠加（×{RAIN * NIGHT:.2f}）。定性理由是湿滑路面制动距离变长、夜间视距变短；系数本身是初值，未经标定。模式由语音切换。")
heading("5.5  防误报与解除", 2)
para(f"（1）升级需连续 {CONFIRM} 帧满足条件，降级立即生效；（2）目标消失超过 {RELEASE_S} s 后解除告警并上报事件，这一判断在主循环中按时间进行，雷达不出帧（如无目标或串口松脱）时也能解除；（3）非作业模式不累计确认、不记录通过事件，结束作业立即解除；（4）可用雷达配置收窄检测范围；（5）最低速度过滤静止物和慢速行人。")

heading("6  组网通信与平台", 1)
heading("6.1  ESP-NOW 广播组网", 2)
para(f"ESP-NOW 是乐鑫定义的无连接 Wi-Fi 通信方式，数据封装在厂商自定义的 action 帧中，设备间无需建立连接{R('esp_now')}。所有报文带公共包头（魔数 0x5C、版本、类型、节点号、节点类型、32 位序号），节点上电随机起号。哨兵在等级变化时立即发送，预警期间每 {REPEAT_MS} ms 重发；联动锥桶对新序号随机退避 2～15 ms 后转发，预警包最多 {MAX_HOPS} 跳，模式配置包每个序号只转发一次。联动锥桶、工人端和网关按发送者去重：同号丢弃，比上次小但相差不到 64 视为迟到副本，相差更多视为对方重启。工人端只对预警包去重，避免迟到的中继副本把已解除的告警重新打开。模式不是作业中时，接收端回到安全。联动锥桶和工人端 {LINK_TIMEOUT_S} s 收不到刷新即回到安全状态。")
table_caption("表 5  ESP-NOW 报文类型")
table([["类型", "内容", "发送时机", "是否转发"],
       ["预警 AlertPkt", "等级、模式、车速、距离、TTC、跳数", f"等级变化立即发送，预警中每 {REPEAT_MS} ms", f"是，≤{MAX_HOPS} 跳"],
       ["心跳 HeartbeatPkt", "电压、模式、等级、信号强度", "每 5 s", "否"],
       ["配置 ConfigPkt", "作业模式位", "模式变化时连发 3 次", "是，每序号一次"],
       ["事件 EventPkt", "最高等级、最高车速、最小 TTC、最近距离、持续时间", "一次接近结束时", "否"]],
      widths=[3.2, 5.6, 4.6, 2.4], size=10)
heading("6.2  安全管理平台", 2)
para("网关把报文转为 MQTT 消息（主题 cone/<节点号>/<类型>）。平台采用 Python FastAPI + SQLite，订阅后写入节点、预警和事件表；网页看板显示节点在线与电量、实时车速与 TTC 曲线、接近事件列表和文字报告（图 7）。格式错误的消息只记日志、不入库；没有事件时统计值为空，报告写明“该时段没有记录到车辆通过事件”。")
figure(IMG + "dashboard_sim.png", 15.0, "图 7  安全看板（2026-11-03 本机 Mosquitto + 模拟器截图，非实测）")
heading("6.3  离线语音", 2)
para("ASRPRO 识别“开始作业/结束作业”“左侧/右侧封道”“雨天模式开/关”“夜间模式开/关”“报告电量”“设备自检”，以 4 字节帧（AA 55 CMD SUM，9600 8N1）发给哨兵，哨兵切换模式后广播配置包。")

heading("7  测试与验证", 1)
heading("7.1  已完成的软件验证", 2)
for s in [f"（1）固件编译（2026-11-03）：哨兵、联动、工人端、网关四个草图在 {CORE}（arduino-cli 1.5.1，FQBN {FQBN}，Adafruit NeoPixel 1.15.5、PubSubClient 2.8）下编译通过，--warnings all 无警告。程序空间（上限 1310720 字节）：{FLASH_DETAIL}。动态内存（上限 327680 字节）：{RAM_DETAIL}。尚未烧录。",
          f"（2）单元测试（2026-11-03，Python 3.12.3）：Python 参考实现 {TESTS} 项测试通过，覆盖阈值边界、三帧确认、非作业模式、LD2451 官方示例帧、语音帧校验、序号去重、MQTT 坏消息与空报告，并直接读取固件头文件，检查阈值、卡尔曼参数、语音命令码、模式位和去重窗口与 Python 一致。",
          "（3）平台联调（2026-11-03）：本机 Mosquitto 2.0.18 + `python -m sentinel` + `tools/simulator.py`。模拟器按固件同一套三帧确认发布预警。第一次通过在日志中为最高等级 2、最高车速 37.32 km/h、最小 TTC 1.08 s、最近 11.24 m、持续 10301 ms；五个节点心跳在线，统计和文字报告与该事件一致（图 7）。这是模拟数据，不是路试。",
          "（4）算法仿真：55 km/h 车辆从 100 m 驶向哨兵，距离量测加入 σ = 2 m 噪声。滤波后曲线平滑；因车速超过限速 20%，连续 3 帧后进入一级预警，TTC 降至 2.5 s 以下时升级为二级（图 8）。",
          "以上验证不涉及实物，不能代替外场测试。"]:
    para(s)
figure(IMG + "sim_curve.png", 13.5, "图 8  仿真：55 km/h 车辆驶向作业区的预警过程")
heading("7.2  预警时间窗口（理论计算）", 2)
para(f"按雷达标称最远探测距离 100 m 计算，可用时间 t = 100 / (v/3.6)：{SPEED_LIMIT} km/h 时约 9.0 s，60 km/h 时约 6.0 s，均大于一级阈值 {TTC1:g} s；车速高于 72 km/h 时不足 {TTC1:g} s，但此时已超过 {SPEED_LIMIT} × {OVERSPEED} km/h，会按超速条件触发一级。实际探测距离受安装高度、车型和天气影响，需实测（图 9）。限速较高的路段可考虑前后两个哨兵级联，作为后续研究。")
figure(IMG + "lead_time.png", 12.5, "图 9  雷达标称探测距离对应的时间窗口（理论计算）")
heading("7.3  封闭场地实测（待完成）", 2)
para("测试只在封闭场地进行，使用自行车或电动车，车速不超过 30 km/h，专人警戒，不用车辆冲向真人。目标值为团队自定验收线。")
table_caption("表 6  实测指标")
table([["指标", "目标值", "测试方法", "实测值"],
       ["测速误差", "≤ ±3 km/h", "10～30 km/h 五档各 5 次，对比测速仪", "【待补充】"],
       ["测距误差", "≤ ±2 m", "路面每 10 m 标记，对比雷达读数", "【待补充】"],
       ["最远稳定检测距离", "≥ 80 m", "白天/夜间/小雨各 5 次", "【待补充】"],
       ["一级预警提前量", "≥ 4 s", "视频逐帧计时", "【待补充】"],
       ["误报率", "≤ 5%", "30 min 无目标驶近观察", "【待补充】"],
       ["漏报率", "≤ 2%", "20 次超阈值驶近", "【待补充】"],
       ["联动延迟", "≤ 100 ms", "慢动作视频逐帧，10 次", "【待补充】"],
       ["续航", "≥ 8 h", "满电连续运行", "【待补充】"]],
      widths=[4.2, 2.4, 6.2, 3.0], size=10)

heading("8  创新点", 1)
for s in ["（1）**按危险程度提醒**：TTC 与超速双判据分级，平时慢闪、危险时升级。",
          "（2）**司机与工人同步提醒**：同一等级同时驱动锥桶灯光和工人穿戴端。",
          "（3）**无基础设施组网**：ESP-NOW 广播、序号去重、两跳中继，模式切换可传到远端锥桶。",
          "（4）**环境系数与语音部署**：雨天、夜间系数一句话切换。",
          "（5）**接近事件结构化记录**：为阈值标定和安全管理积累原始数据。",
          "以上为设计特点，实际效果需对比试验验证。"]:
    para(s)

heading("9  应用前景", 1)
para("可能的用户包括公路养护单位、市政道路养护单位、高速公路运营单位以及路政、交警部门；可能的形式包括整套锥桶、灯头改装模块和数据平台服务。推广路径：完成样机 → 封闭场地测试与标定 → 与养护单位小范围试用 → 根据反馈改进结构与防护。【待补充：调研 2～3 家养护单位的作业频次、现有设施、采购意愿和可接受价格】")
heading("10  不足与改进方向", 1)
for s in ["（1）尚未完成实物测试，阈值和环境系数需依据封闭场地数据标定；",
          "（2）心跳和事件包不经中继，网关需在直接通信范围内；",
          "（3）MQTT broker 默认允许匿名访问，只适合实验室，接入单位网络前需增加认证与加密；",
          "（4）计划加装光敏、雨滴传感器自动识别环境，并尝试“距离—速度”二维卡尔曼滤波；",
          "（5）计划完成 PCB 集成与防水外壳。"]:
    para(s)

heading("参考文献", 1)
for i, (text, url) in enumerate(REFS, start=1):
    p = para(f"[{i}] {text}. {url}", indent=False, size=10.5)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Pt(21); p.paragraph_format.first_line_indent = Pt(-21)
para("【待补充：国内期刊或学位论文 3～5 篇，逐条打开原文后按 GB/T 7714 著录】", indent=False, size=10.5)

out = "./哨兵_挑战杯作品申报书.docx"
doc.save(out)
print(out)
