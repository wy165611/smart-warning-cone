# -*- coding: utf-8 -*-
"""生成 挑战杯（大挑）科技发明制作类 作品申报书 + 作品研究报告（说明书）"""
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

IMG = "img/"
TITLE = "哨兵——基于毫米波雷达与协同组网的公路养护作业区智能预警锥桶系统"
PH = re.compile(r"(【填[^】]*】)")

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
# 封面
# =====================================================================
for _ in range(2):
    doc.add_paragraph()
para("第二十届“挑战杯”全国大学生课外学术科技作品竞赛", indent=False, align="c", size=16, east="黑体", bold=True)
doc.add_paragraph()
para("作 品 申 报 书", indent=False, align="c", size=36, east="黑体", bold=True)
for _ in range(3):
    doc.add_paragraph()
cover = [
    ("作品名称：", TITLE),
    ("学校全称：", "山东理工大学"),
    ("申报者姓名\n（集体名称）：", "【填：集体作品写团队名称，如“哨兵”团队】"),
    ("类    别：", "□ 自然科学类学术论文\n□ 哲学社会科学类社会调查报告\n□ 科技发明制作 A 类\n☑ 科技发明制作 B 类"),
]
t = doc.add_table(rows=len(cover), cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, (k, v) in enumerate(cover):
    cell_text(t.cell(i, 0), k, size=14, bold=True, east="黑体", align="l")
    cell_text(t.cell(i, 1), v, size=14, align="l")
fix_widths(t, [4.4, 10.8])
for _ in range(4):
    doc.add_paragraph()
para("【填：申报日期，如 2027 年 × 月 × 日】", indent=False, align="c", size=14)
para("说明：类别以作品发明点或创新点所在类别填写。本作品投入较少、为公路养护作业安全带来直接便利，建议申报科技发明制作 B 类；如学校评审认为技术含量与投入达到 A 类要求，可改为 A 类。", indent=False, size=10.5, color="666666")
page_break()

# =====================================================================
# 填写说明
# =====================================================================
heading("说  明", 0)
notes = [
    "1．申报者应在认真阅读本说明各项内容后按要求详细填写。",
    "2．申报者在填写申报作品情况时只需根据作品类别（自然科学类学术论文、哲学社会科学类社会调查报告、科技发明制作）填写相应栏目，本作品属于科技发明制作类，填写 A 及 B3 部分。",
    "3．表内项目填写时一律用钢笔或打印，字迹要端正、清楚，此申报书可复制，表格大小可适当调整。",
    "4．序号、编码由竞赛组委会填写。",
    "5．科技发明制作类作品须附研究报告（科技发明制作说明书），并提供图表、曲线、试验数据、原理结构图、外观图（照片），也可附鉴定证书和应用证书。研究报告见本申报书附件。",
    "6．作品申报须经过学校公示（不少于 5 天），并将公示截图随作品一同报送。",
    "7．本申报书中黄色底纹的【填】处为必须由申报者据实填写的内容，提交前务必全部替换并删除底纹。",
]
for n in notes:
    para(n, indent=False)
para("注：以上说明依据历届“挑战杯”作品申报书通行格式整理，正式提交时请以本届组委会下发的申报书模板为准，逐栏誊入。", indent=False, size=10.5, color="666666")
page_break()

# =====================================================================
# A. 申报者情况
# =====================================================================
heading("A. 申报者情况（集体作品）", 1)
para("说明：1．必须由申报者本人按要求填写；2．申报者代表必须是作者中学历最高者，其余作者按学历高低排列；3．本表中的学籍管理部门签章视为对申报者情况的确认。", indent=False, size=10.5)
rows = [["", "姓名", "性别", "年龄", "学历", "所在单位（学院/专业/年级）", "分工"]]
roles = ["负责人：需求调研、预警算法、测试方案、申报书", "硬件选型、电路与 PCB、电源、固件", "ESP-NOW 组网、云平台开发", "外壳结构、市场调研、答辩与视频"]
for i, r in enumerate(roles):
    rows.append(["申报者代表" if i == 0 else f"其他作者{i}", "【填】", "", "", "本科", "【填】", r])
table(rows, widths=[1.8, 1.6, 1.3, 1.3, 1.1, 3.9, 4.8], size=9.5)
rows = [["项目", "内容"],
        ["申报者代表通讯地址", "【填：学校地址、邮编】"],
        ["联系电话 / 电子邮箱", "【填】"],
        ["指导教师", "【填：姓名、职称、所在单位】"],
        ["资格认定（学籍管理部门意见）", "以上作者是否为 2027 年 6 月 1 日前正式注册在校的全日制非成人教育、非在职的高等学校中国籍本科生或研究生。\n是 □    否 □\n\n（学籍管理部门签章）            年    月    日"],
        ["资格认定（院、系、所或年级意见）", "本作品是否为课外学术科技或社会实践活动成果。\n是 □    否 □\n负责人签名：                      年    月    日"]]
table(rows, widths=[4.4, 11.4], size=10.5, align_body="l")
para("注：作者人数按本届章程要求核对（超过 3 人或无法区分第一作者的须申报集体作品）；参赛资格时间节点以本届通知为准。", indent=False, size=10.5, color="666666")

heading("申报者声明", 2)
para("我（们）郑重声明：所提交的作品为本人（团队）在指导教师指导下独立完成的课外学术科技成果，作品中引用他人成果之处均已注明出处；作品未以同一内容参加过“挑战杯”系列竞赛及其他全国性竞赛评奖；如有违反，愿承担一切后果。")
para("申报者代表签名：                    日期：      年    月    日", indent=False, align="r")
page_break()

# =====================================================================
# B3. 申报作品情况（科技发明制作）
# =====================================================================
heading("B3. 申报作品情况（科技发明制作）", 1)
para("说明：1．必须由申报者本人填写；2．本部分中的科研管理部门签章视为对申报者所填内容的确认；3．本表必须附有研究报告，并提供图表、曲线、试验数据、原理结构图、外观图（照片），也可附鉴定证书和应用证书；4．作品分类请按照作品发明点或创新点所在类别填报。", indent=False, size=10.5)

b3_purpose = """**一、目的**
公路养护作业多在不封闭交通的条件下进行，作业人员背对来车、注意力集中在路面，一旦车辆超速或分心驶入作业区，后果往往十分严重。美国联邦公路管理局（FHWA）数据显示，2024 年美国作业区交通事故造成 850 人死亡，其中约 22% 的致死事故涉及追尾，超过一半发生在夜间。我国截至 2024 年末公路里程达 549.04 万公里，其中农村公路 464.37 万公里，日常小修保养点多、量大、作业时间短，普遍只摆放锥桶、标志牌等被动设施，缺少能“看见”来车风险的主动预警手段。本作品旨在以百元级成本，让普通锥桶具备感知、判断、联动和数据记录能力，为县乡道路和城市道路的小型养护作业提供用得起、即放即用的主动安全防护。
**二、基本思路**
在作业区上游放置一个搭载 24GHz 毫米波雷达的“哨兵锥桶”，实时测量来车距离与速度，计算碰撞时间（TTC）并分级预警；沿过渡区布设若干“联动锥桶”，通过 ESP-NOW 自组网接收预警并依次点亮，形成指向变道方向的流水灯；工人佩戴报警器，在二级预警时震动+蜂鸣提醒撤离；网关把预警和“危险接近事件”上传平台，自动生成作业区安全报告。全部判定在锥桶本地完成，无网络也能工作。
**三、创新点**
1．由“被动隔离”到“主动感知”：在标准锥桶顶部卡装雷达灯头模块，不改变现有设施即可升级；
2．基于 TTC 的三级预警与环境自适应阈值：同时考虑接近时间与超速，雨天、夜间自动放宽阈值；
3．锥桶自组网协同：无路由器、毫秒级广播、序号去重与两跳中继，联动锥桶按位置延时形成流水灯；
4．工人端主动撤离提醒：把预警直接送到背对来车的工人身上；
5．离线语音部署：戴手套、站在路上也能一句话完成开始作业、封道方向、雨天/夜间模式切换；
6．作业区风险数据化：记录每次车辆通过的最高车速、最小 TTC、最近距离，形成可追溯的安全台账。
**四、技术关键**
1．毫米波雷达协议解析与多目标中“最危险目标”选择；2．卡尔曼滤波抑制距离/速度跳变；3．连续 3 帧确认 + 1.5 s 保持的防误报/防闪断策略；4．低功耗广播组网的去重、退避与重启兼容；5．户外供电（雷达需 5 V、>200 mA）与防水结构。
**五、主要技术指标**（设计值，实测值见研究报告第 7 章）
探测距离 ≤100 m（雷达器件指标，10–100 m 可调）；水平探测角 ±15°；数据刷新约 10 Hz；预警等级 3 级；预警确认时间约 0.3 s；联动延迟目标 ≤100 ms；中继跳数 ≤2；单个哨兵节点物料成本约 115 元，演示套装（1 哨兵+2 联动+1 工人端+1 网关）约 350 元；续航目标 ≥8 h（3000 mAh 18650）。"""

b3_sci = """**1．科学性**
（1）判定依据可靠：TTC 是交通冲突技术中衡量碰撞紧迫程度的经典指标（Hayward，1972），TTC = d / v，物理意义清晰；一级阈值 5 s、二级阈值 2.5 s 分别对应“留足减速/变道时间”和“接近驾驶员最短反应时间”，并可按实测标定。
（2）测量手段适合户外：24GHz FMCW 毫米波雷达可同时输出距离、速度、方向和角度，受光照、雨雾影响小，优于超声波（作用距离仅数米）和摄像头（夜间、雨雾性能下降且存在隐私问题）。
（3）信号处理有依据：采用一维卡尔曼滤波（Kalman，1960）平滑距离与速度；仿真表明在 2 m 量测噪声下能稳定跟踪来车并在 TTC 跨越阈值时正确升级（研究报告图 7）。
（4）工程实现已验证：四类节点固件均已基于 ESP32 Arduino 核心 3.3.12 编译通过；平台端 MQTT→数据库→看板→报告链路已用模拟器端到端联调通过。
**2．先进性（与现有技术对比）**
| 现有方式 | 不足 | 本作品 |
| 锥桶/水马/标志牌 | 只能隔离提示，无感知 | 雷达感知来车，分级预警 |
| 太阳能爆闪灯 | 固定频率闪烁，司机易“习惯性忽略” | 平时慢闪，危险时爆闪+流水灯，差异化刺激 |
| 作业区入侵报警（压力管、红外对射） | 车辆已闯入才报警，提前量不足 | 车辆距作业区数十米时即预警 |
| 智慧作业区系统（雷达+情报板+平台） | 价格高、需专业安装，多用于高速公路大型作业 | 百元级、即放即用、可组网 |
| 防撞缓冲车 | 减轻后果而非预防，成本高 | 事前预警，可与缓冲车互补 |
**突出的实质性技术特点**：①预警由“有无车辆”升级为“危险程度”（TTC+超速双判据）；②预警对象同时覆盖司机（灯光）和工人（震动）；③锥桶间无基础设施组网并带两跳中继；④每次接近事件结构化入库，可量化作业区风险。
**显著进步**：以百元级成本实现“感知—判定—联动—记录”闭环，使主动预警能够从高速公路大型作业延伸到县乡道路、城市道路日常小型养护。
参考文献：见研究报告“参考文献”。"""

b3_use = """**一、使用说明**
1．部署：按 GB 5768.4—2017《道路交通标志和标线 第 4 部分：作业区》和 JTG H30—2015《公路养护安全作业规程》设置作业区后，把哨兵锥桶放在上游警告区（距作业区 50–150 m，按限速与视距确定），雷达面朝来车；联动锥桶沿上游过渡区摆放；工人佩戴报警器；网关放在作业车上。
2．启动：对哨兵说“开始作业”，语音回复确认后系统进入工作状态；按需说“左侧封道/右侧封道”“雨天模式”“夜间模式”。
3．运行：安全时黄灯慢闪；一级预警红黄快闪、联动锥桶流水灯；二级预警红色爆闪+蜂鸣，工人报警器震动。
4．收工：说“结束作业”，平台自动生成本次作业安全报告。
**二、技术特点和优势**
低成本（哨兵约 115 元）；即放即用（卡装在标准 70 cm 锥桶上，无需布线和专业安装）；全天候（毫米波雷达）；离线可靠（判定在本地，网络中断不影响预警）；可扩展（节点数量按作业区长度增减，平台支持多作业区）。
**三、适用范围**
县乡道路、城市道路、高速公路的小修保养、路面修补、标线施划、绿化养护；交通事故现场临时管控、路政巡查临时停车点；市政管线开挖等占道作业。
**四、推广前景与市场分析**
截至 2024 年末，全国公路里程 549.04 万公里，其中农村公路 464.37 万公里（县道 69.88、乡道 124.34、村道 270.14 万公里）、高速公路 19.07 万公里。“四好农村路”养护常态化使小型养护作业点数量巨大，而现有智慧作业区产品主要面向高速公路大型作业，县乡道路小型养护中的应用仍然较少。政策层面，《交通强国建设纲要》、交通运输部《关于推进公路数字化转型 加快智慧公路建设发展的意见》、国务院安委会《安全生产治本攻坚三年行动方案（2024—2026 年）》均对公路安全与数字化提出明确要求，产品契合政策方向。
目标客户：公路养护公司、市政道路养护单位、高速公路运营公司、交警与路政部门、施工单位。商业模式：智能锥桶套装销售；只卖“灯头模块”的改装套件；安全数据平台按年订阅。
**五、经济效益预测**（按以下假设测算，需结合调研修正）
量产后单个哨兵节点 BOM 预计可降至 80 元以内（批量采购与 PCB 集成），套装（1 哨兵+4 联动+2 工人端+网关）售价按【填：调研后确定，如 1500 元】计。【填：目标区域养护班组数量】个班组按 10% 渗透率测算，可得销售额【填】万元。社会效益：每避免 1 起作业区伤亡事故，可减少的直接经济损失与社会成本远高于设备投入。"""

rows = [
    ["作品全称", TITLE],
    ["作品分类", "（ A ）A．机械与控制（包括机械、仪器仪表、自动化控制、工程、交通、建筑等）\n         B．信息技术（包括计算机、电信、通讯、电子等）\n         C．数理  D．生命科学  E．能源化工\n注：本作品发明点在交通工程安全与自动化预警，建议选 A；若学校按电子信息归口，可改选 B。"],
    ["作品设计、发明的目的和基本思路，创新点，技术关键和主要技术指标", b3_purpose],
    ["作品的科学性、先进性（必须说明与现有技术相比、该作品是否具有突出的实质性技术特点和显著进步。请提供技术性分析说明和参考文献资料）", b3_sci],
    ["作品在何时、何地、何种机构举行的评审、鉴定、评比、展示等活动中获奖及鉴定结果", "【填：如校赛/省赛获奖情况；无则填“无”】"],
    ["作品所处阶段", "（ A ）A．实验室阶段  B．中试阶段  C．生产阶段  D．（自填）\n说明：已完成系统方案、全部固件与平台软件，固件编译通过、平台仿真联调通过；【填：实物样机完成情况与封闭场地测试情况】。"],
    ["技术转让方式", "【填：如“专利许可或与养护企业合作开发”；暂无则填“暂无”】"],
    ["作品可展示的形式", "☑ 实物、产品  □ 模型  ☑ 图纸  □ 磁盘\n☑ 现场演示  ☑ 图片  ☑ 录像  □ 样品"],
    ["使用说明及该作品的技术特点和优势，提供该作品的适应范围及推广前景的技术性说明及市场分析和经济效益预测", b3_use],
    ["专利申请情况", "□ 提出专利申请    申请号：【填】    申请日期：【填】\n□ 已获专利权批准  批准号：【填】    批准日期：【填】\n□ 未提出专利申请\n建议：赛前以学生为第一发明人申请实用新型专利 1 项（智能预警锥桶灯头模块结构与组网预警方法）、软件著作权 1 项（作业区安全管理平台）。"],
]
t = doc.add_table(rows=len(rows), cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER


def fill_rich(cell, text, size=10):
    """单元格内容：支持 | 表格行 渲染为嵌套表"""
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
                    if r == 0: shade(nt.cell(r, c))
            fix_widths(nt, [2.9, 4.4, 4.6])
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
para("说明：1．由推荐者本人填写；2．推荐者必须具有高级专业技术职称，并是与申报作品相同或相关领域的专家学者或专业技术人员（教学、科研或企业技术部门工作人员）；3．推荐者填写此部分，即视为同意推荐；4．推荐者所在单位签章仅被视为对推荐者身份的确认。", indent=False, size=10.5)
for n in (1, 2):
    rows = [["推荐者情况", "姓名：【填】  性别：【填】  年龄：【填】  职称：【填】\n工作单位：【填】\n通讯地址：【填】    邮编：【填】    电话：【填】"],
            ["推荐者所在单位签章", "\n（签章）                    年    月    日"],
            ["请对申报者申报情况的真实性作出阐述", "【填：推荐者本人撰写】"],
            ["请对作品的意义、技术水平、适用范围及推广前景作出您的评价", "【填：推荐者本人撰写。可参考：该作品针对公路养护作业区“被动防护、预警滞后”的问题，以毫米波雷达测距测速和碰撞时间判定实现分级主动预警，结合锥桶自组网联动和工人端撤离提醒，技术路线合理、成本低、易推广……】"],
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
pg = OxmlElement('w:pgNumType'); pg.set(qn('w:start'), '1'); new._sectPr.append(pg)
add_page_number(new)
heading("附件  作品研究报告（科技发明制作说明书）", 0)
para(TITLE, indent=False, align="c", size=14, east="黑体", bold=True, space_after=6)

heading("摘  要", 2)
para("公路养护作业区是道路交通安全的薄弱环节，现有锥桶、标志牌等设施只能被动隔离，无法感知来车风险，智慧作业区系统又因价格高、安装复杂难以用于县乡道路和城市道路的日常小型养护。本作品设计了一套百元级的智能预警锥桶系统“哨兵”：上游哨兵锥桶以 24GHz 毫米波雷达测量来车距离与速度，经卡尔曼滤波后计算碰撞时间（TTC），按 TTC 与超速双判据进行三级预警，并依据雨天、夜间自动调整阈值；多个锥桶通过 ESP-NOW 自组网联动形成流水灯引导变道；工人报警器在二级预警时震动提醒撤离；离线语音模块支持一句话部署；网关将预警与“危险接近事件”上传平台，自动生成作业区安全报告。系统四类节点固件已编译通过，平台已与模拟器端到端联调；理论分析表明，在 40 km/h 限速作业区，雷达 100 m 探测距离可提供约 9 s 的预警窗口。单个哨兵节点物料成本约 115 元，具备大范围推广条件。")
para("**关键词**：公路养护；作业区安全；毫米波雷达；碰撞时间；ESP-NOW；协同预警", indent=False)

heading("1  研究背景与意义", 1)
heading("1.1  作业区安全问题突出", 2)
para("养护作业通常“边通车、边施工”。作业人员面向路面、背对来车，施工机械噪声大，往往在车辆已经很近时才察觉危险；司机则可能因超速、疲劳、使用手机或夜间视距不足而未能及时发现作业区。国外统计显示，2024 年美国作业区交通事故死亡 850 人，涉及追尾的致死事故约占 22%，超过一半的致死事故发生在夜间（FHWA，2026）。我国【填：引用国内作业区事故统计或典型事故案例，建议检索交通运输部、应急管理部公开通报及中国知网相关文献】。")
figure(IMG + "workzone.png", 14.5, "图 1  县乡道路养护作业区示意（概念图，正式稿请替换为团队实拍照片）")
heading("1.2  现有设施的不足", 2)
for s in ["（1）被动：锥桶、水马、标志牌只能隔离和提示，不能判断某辆车是否超速、是否在接近作业区却没有减速。",
          "（2）同质化：太阳能爆闪灯始终以固定频率闪烁，不区分危险程度，司机容易“习惯性忽略”。",
          "（3）滞后：压力管、红外对射类入侵报警器在车辆已闯入作业区时才报警，给工人的撤离时间不足。",
          "（4）昂贵：智慧作业区系统、防撞缓冲车价格高、需要专业安装，主要用于高速公路大型作业。",
          "（5）无数据：养护单位无法量化“作业区到底有多危险”，安全管理依赖经验。"]:
    para(s)
heading("1.3  研究意义", 2)
para("截至 2024 年末，我国公路里程 549.04 万公里，其中农村公路 464.37 万公里（交通运输部，2025）。日常小修保养作业点分散、频次高、单次时间短，最需要“用得起、拿来就能用”的主动预警设备。本作品以百元级成本让传统锥桶具备感知、判断、联动与记录能力，对保护一线养护工人生命安全、推动公路养护数字化具有现实意义，契合《交通强国建设纲要》《关于推进公路数字化转型 加快智慧公路建设发展的意见》和《安全生产治本攻坚三年行动方案（2024—2026 年）》的要求。")

heading("2  国内外研究现状", 1)
para("作业区安全研究主要集中在交通组织设计（警告区、过渡区长度与限速取值）、驾驶行为分析和防撞缓冲设施等方面。主动预警方面，国外较早应用作业区入侵报警装置（Work Zone Intrusion Alarm）和基于雷达的动态速度反馈标志；国内部分高速公路开展了智慧作业区试点，采用雷达、情报板和平台联动。【填：补充 3～5 篇国内外文献的作者、方法与结论，建议在中国知网检索“养护作业区 预警”“work zone intrusion alarm”等关键词】。")
table_caption("表 1  现有作业区安全设施对比")
table([["类型", "典型形式", "不足", "本作品的改进"],
       ["传统设施", "锥桶、水马、标志牌", "无感知、无预警", "加装雷达灯头，主动感知"],
       ["爆闪灯", "太阳能定频爆闪", "不分危险程度，易被忽略", "分级灯光 + 流水灯"],
       ["入侵报警", "压力管、红外对射", "闯入后才报警，提前量不足", "数十米外按 TTC 提前预警"],
       ["智慧作业区", "雷达 + 情报板 + 平台", "价格高、安装复杂", "百元级、即放即用"],
       ["防撞缓冲车", "车载吸能装置", "减轻后果，成本高", "事前预警，可与之互补"]],
      widths=[2.4, 3.6, 4.8, 5.0], size=10)

heading("3  系统总体设计", 1)
heading("3.1  设计目标", 2)
para("（1）提前：在车辆到达作业区前留出足够的减速、变道和撤离时间；（2）分级：只在真正危险时强提醒，避免“一直闪、没人看”；（3）可靠：本地判定、离线可用、防误报；（4）低成本、易部署：不改造现有锥桶，一人即可完成布设；（5）可追溯：记录危险接近事件，量化作业区风险。")
heading("3.2  系统架构", 2)
para("系统由感知层、边缘决策与组网层、平台层组成（图 2）。哨兵锥桶负责感知与判定；联动锥桶和工人报警器负责执行预警；网关把 ESP-NOW 数据转换为 MQTT 上传；平台负责存储、展示与报告。")
figure(IMG + "arch.png", 15.5, "图 2  系统总体架构")
heading("3.3  现场布设", 2)
para("哨兵锥桶放置在上游警告区，距作业区 50–150 m，雷达面朝来车方向；联动锥桶沿上游过渡区斜向布设，按距哨兵由近及远依次点亮，形成指向变道方向的流水灯；工人佩戴报警器；网关放在作业车上（图 3）。")
figure(IMG + "layout.png", 15.5, "图 3  作业区布设俯视示意")

heading("4  硬件设计", 1)
figure(IMG + "hw.png", 13.5, "图 4  哨兵锥桶硬件框图")
table_caption("表 2  哨兵锥桶主要器件选型")
table([["模块", "型号/方案", "关键参数", "选型理由"],
       ["主控", "ESP32-C3", "RISC-V 160 MHz，Wi-Fi/BLE，ESP-NOW", "低成本，原生支持无路由组网"],
       ["雷达", "HLK-LD2451", "24–24.25 GHz FMCW，≤100 m，±15°，5 V/>200 mA", "专为车辆检测，输出距离/速度/方向/角度"],
       ["灯光", "WS2812B 灯环 30 灯", "可编程 RGB", "实现分级与流水灯"],
       ["声音", "有源蜂鸣器 + AO3400", "MOSFET 低边驱动", "二级预警声报警"],
       ["语音", "ASRPRO V2.0", "离线识别，UART 9600", "无网络、戴手套也能操作"],
       ["电源", "18650 3000 mAh + TP4056 + 5 V 升压", "满足雷达 5 V 供电", "野外独立供电，可扩展太阳能"],
       ["结构", "3D 打印灯头，卡装锥桶顶部", "PETG，防水接头", "不改造现有锥桶"]],
      widths=[1.6, 3.8, 5.6, 4.8], size=9.5)
para("联动锥桶去掉雷达与语音模块，只保留主控、灯环、蜂鸣器和电源；工人报警器采用 ESP32-C3、扁平振动马达、蜂鸣器和 500 mAh 小锂电，佩戴在安全帽或背心上；网关为 USB 供电的 ESP32 开发板。")
table_caption("表 3  演示套装物料成本（估算，按实际采购修正）")
table([["组成", "数量", "单价（元，约）", "小计（元，约）"],
       ["哨兵锥桶模块", "1", "115", "115"],
       ["联动锥桶模块", "2", "45", "90"],
       ["工人报警器", "1", "31", "31"],
       ["网关", "1", "12", "12"],
       ["锥桶、外壳、辅料", "—", "—", "100"],
       ["合计", "", "", "≈350"]], widths=[5.3, 2.5, 4.0, 4.0], size=10)

heading("5  核心算法", 1)
figure(IMG + "flow.png", 15.5, "图 5  哨兵锥桶预警判定流程")
heading("5.1  雷达数据解析与目标筛选", 2)
para("LD2451 通过串口（115200 bps，8N1）输出检测结果，帧头 F4 F3 F2 F1、帧尾 F8 F7 F6 F5，每个目标包含角度、距离、方向、速度和信噪比；有目标时约 100 ms 输出一帧，无目标时约 1 s 一帧（海凌科，2024）。程序只保留方向为“靠近”、速度不小于 5 km/h、距离不大于 100 m 的目标，以排除行人、远离车辆和静止干扰。")
heading("5.2  卡尔曼滤波", 2)
para("对距离量测 z 采用一维常值模型滤波：")
formula("P⁻ = P + Q，   K = P⁻ /(P⁻ + R)，   x = x + K(z − x)，   P = (1 − K)P⁻")
para("其中 Q = 0.5、R = 4 为初始参数，可用实测数据离线标定。滤波后距离曲线平滑，TTC 不会因单帧跳变而误触发（图 7）。")
heading("5.3  碰撞时间与三级预警", 2)
para("碰撞时间定义为车辆保持当前速度到达哨兵位置所需的时间：")
formula("TTC = d / (v / 3.6)        （d：m；v：km/h；TTC：s）")
para("当多个目标同时存在时，选 TTC 最小者为当前威胁目标。预警等级判定见表 4，判定区域见图 6。")
table_caption("表 4  预警分级规则（默认参数，可配置）")
table([["等级", "触发条件", "哨兵 / 联动锥桶", "工人报警器"],
       ["安全", "无接近目标或 TTC ≥ 5 s 且未超速", "黄灯慢闪", "静默"],
       ["一级", "TTC < 5 s，或车速 > 限速 × 1.2", "红黄快闪 + 流水灯", "LED 提示"],
       ["二级", "TTC < 2.5 s", "红色爆闪 + 蜂鸣", "强震动 + 蜂鸣"]],
      widths=[1.6, 5.4, 4.4, 4.4], size=10)
figure(IMG + "ttc_map.png", 12.5, "图 6  基于 TTC 的三级预警判定区域（限速 40 km/h）")
heading("5.4  环境自适应阈值", 2)
para("雨天路面附着系数降低、制动距离增加，夜间视距缩短、反应时间变长，因此雨天模式将 TTC 阈值乘以 1.4，夜间模式乘以 1.2，两者可叠加（×1.68）。模式可通过语音切换，后续可加装光敏和雨滴传感器自动识别。")
heading("5.5  防误报与防闪断", 2)
para("（1）升级需连续 3 帧（约 0.3 s）满足条件；（2）目标消失后保持 1.5 s 再解除，防止灯光闪断；（3）在雷达配置中收窄探测角度，只关注本车道及相邻车道；（4）结合最低速度过滤静止物与慢速行人。")

heading("6  组网通信与平台", 1)
heading("6.1  ESP-NOW 自组网", 2)
para("节点间采用 ESP-NOW 广播，无需路由器即可点对多点通信。所有数据包带公共包头（魔数 0x5C、版本、类型、节点号、节点类型、32 位序号）。哨兵在等级变化时立即发送，预警期间每 200 ms 重发；联动锥桶收到新序号后随机退避 2～15 ms 转发一次，最多 2 跳，以扩大覆盖范围；接收端按“节点号+序号”去重，节点上电以随机序号起始，避免重启后被误判为旧包。联动锥桶按自身编号延时点亮，形成流水灯。")
table_caption("表 5  ESP-NOW 报文类型")
table([["类型", "内容", "发送时机"],
       ["预警 AlertPkt", "等级、模式、车速、距离、TTC、跳数", "等级变化立即发送，预警中每 200 ms"],
       ["心跳 HeartbeatPkt", "电压、模式、等级、信号强度", "每 5 s"],
       ["配置 ConfigPkt", "作业模式位", "模式变化时连发 3 次"],
       ["事件 EventPkt", "最高等级、最高车速、最小 TTC、最近距离、持续时间", "一次车辆通过结束时"]],
      widths=[3.6, 7.0, 5.2], size=10)
heading("6.2  安全管理平台", 2)
para("网关把 ESP-NOW 报文转换为 MQTT 消息（主题 cone/<节点号>/<类型>）。平台后端采用 Python FastAPI + SQLite，订阅消息后写入节点表与事件表；网页看板显示锥桶在线状态与电量、实时车速与 TTC 曲线、危险接近事件列表，并自动生成作业区安全报告（通过车辆数、一级/二级预警次数、平均与最高车速、最小 TTC、最危险的 5 次接近）。")
heading("6.3  离线语音", 2)
para("ASRPRO 模块识别“开始作业/结束作业”“左侧/右侧封道”“雨天模式开/关”“夜间模式开/关”“报告电量”等命令，以 4 字节帧（AA 55 CMD SUM）发给哨兵，哨兵同步给全网。")

heading("7  测试与验证", 1)
heading("7.1  已完成的验证", 2)
for s in ["（1）固件编译：哨兵、联动、工人端、网关四个固件在 Arduino-ESP32 核心 3.3.12（ESP32C3 Dev Module）下编译通过，占用程序空间 73%～74%。",
          "（2）平台联调：用模拟器向 MQTT 服务器发送心跳、预警、事件报文，平台节点状态、事件入库、统计接口、安全报告、网页看板均工作正常。",
          "（3）算法仿真：对 55 km/h 车辆从 100 m 驶向哨兵的过程加入 σ = 2 m 的距离量测噪声，滤波后距离曲线平滑；因车速超过限速 20%，系统在 0.3 s 内进入一级预警，在 TTC 降至 2.5 s 时升级为二级预警，过程中无误降级（图 7）。"]:
    para(s)
figure(IMG + "sim_curve.png", 13.5, "图 7  仿真：55 km/h 车辆驶向作业区的预警过程")
heading("7.2  预警时间窗口分析", 2)
para("雷达最远探测距离 100 m 时，可提供的预警时间为 t = 100 / (v / 3.6)。由图 8 可知：车速 40 km/h 时约 9.0 s，60 km/h 时约 6.0 s，均大于一级预警阈值 5 s；车速超过约 72 km/h 时，100 m 探测距离提供的时间不足 5 s，此时系统仍会因超速立即触发一级预警。对于限速较高的路段，建议采用“上游 150 m + 80 m”双哨兵级联，提前感知并可计算车辆在两点间的减速度。")
figure(IMG + "lead_time.png", 12.5, "图 8  雷达探测距离可覆盖的预警时间（理论计算）")
heading("7.3  封闭场地实测（待完成）", 2)
para("测试只在封闭场地进行，使用电动车或自行车，车速不超过 30 km/h，专人警戒，不得用车辆冲撞真人。")
table_caption("表 6  主要性能指标实测结果")
table([["指标", "目标值", "测试方法", "实测值"],
       ["测速误差", "≤ ±3 km/h", "10～30 km/h 五档各 5 次，对比测速仪", "【填】"],
       ["测距误差", "≤ ±2 m", "路面每 10 m 标记，对比雷达读数", "【填】"],
       ["最远稳定检测距离", "≥ 80 m", "白天/夜间/小雨各 5 次", "【填】"],
       ["一级预警提前量（20/30 km/h）", "≥ 4 s", "视频逐帧计时", "【填】"],
       ["误报率", "≤ 5%", "30 min 无目标驶近观察", "【填】"],
       ["漏报率", "≤ 2%", "20 次超阈值驶近", "【填】"],
       ["联动延迟", "≤ 100 ms", "慢动作视频逐帧，10 次", "【填】"],
       ["续航", "≥ 8 h", "满电连续运行", "【填】"]],
      widths=[4.2, 2.4, 6.2, 3.0], size=10)

heading("8  创新点", 1)
for s in ["（1）**主动感知**：在标准锥桶上卡装百元级雷达灯头模块，让作业区“看得见”来车风险。",
          "（2）**分级预警与自适应阈值**：TTC 与超速双判据，雨天、夜间自动调整，提醒有轻重、不扰民。",
          "（3）**锥桶协同组网**：无基础设施广播组网，序号去重与两跳中继，流水灯动态引导变道。",
          "（4）**工人端撤离提醒**：震动+声音直达背对来车的工人，弥补感知盲区。",
          "（5）**离线语音部署**：一句话完成作业开始、封道方向和天气模式设置。",
          "（6）**作业区风险数据化**：结构化记录每次危险接近，形成可追溯的安全台账。"]:
    para(s)

heading("9  应用前景与效益", 1)
para("目标用户包括公路养护公司、市政道路养护单位、高速公路运营公司、交警与路政部门以及占道施工单位。产品可按“智能锥桶套装”“灯头改装套件”“安全数据平台订阅”三种方式推广。按照全国 464.37 万公里农村公路的养护体量，县乡道路小型养护作业对低成本主动预警设备的需求广泛。【填：通过电话或走访调研 2～3 家养护单位，补充其作业频次、现有设施、采购意愿和可接受价格】。")
heading("10  不足与改进方向", 1)
for s in ["（1）目前尚未完成大样本实测，阈值需依据封闭场地和合作单位现场数据标定；",
          "（2）计划加装光敏、雨滴传感器实现天气模式自动识别；",
          "（3）计划采用“距离-速度”二维卡尔曼滤波，并根据车辆减速度判断司机是否已注意到预警，形成预警有效性评价；",
          "（4）计划完成 PCB 集成与 IP65 防护外壳，进一步降低成本、提高可靠性。"]:
    para(s)

heading("参考文献", 1)
refs = ["[1] 交通运输部. 2024年交通运输行业发展统计公报[R]. 北京: 交通运输部, 2025.",
        "[2] 中共中央, 国务院. 交通强国建设纲要[Z]. 2019.",
        "[3] 交通运输部. 关于推进公路数字化转型 加快智慧公路建设发展的意见[Z]. 2023.",
        "[4] 国务院安全生产委员会. 安全生产治本攻坚三年行动方案（2024—2026年）[Z]. 2024.",
        "[5] 中华人民共和国交通运输部. 公路养护安全作业规程: JTG H30—2015[S]. 北京: 人民交通出版社, 2015.",
        "[6] 道路交通标志和标线 第4部分：作业区: GB 5768.4—2017[S]. 北京: 中国标准出版社, 2017.",
        "[7] Federal Highway Administration. 2026 National Work Zone Awareness Week Fact Sheet: FHWA-HOP-26-060[R]. Washington, D.C.: U.S. Department of Transportation, 2026.",
        "[8] Hayward J C. Near-miss determination through use of a scale of danger[J]. Highway Research Record, 1972, 384: 24-34.",
        "[9] Kalman R E. A new approach to linear filtering and prediction problems[J]. Journal of Basic Engineering, 1960, 82(1): 35-45.",
        "[10] 深圳市海凌科电子有限公司. HLK-LD2451 车辆状态检测模组说明书 V1.03[Z]. 2024.",
        "[11] 深圳市海凌科电子有限公司. LD2451 串口通信协议 V1.03[Z]. 2024.",
        "[12] Espressif Systems. ESP-NOW User Guide[EB/OL]. https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/network/esp_now.html.",
        "[13] 【填：补充 3～5 篇中国知网检索到的作业区安全/主动预警相关期刊或学位论文，按 GB/T 7714 格式著录】"]
for r in refs:
    p = para(r, indent=False, size=10.5)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Pt(21); p.paragraph_format.first_line_indent = Pt(-21)

out = "./哨兵_挑战杯作品申报书.docx"
doc.save(out)
print(out)
