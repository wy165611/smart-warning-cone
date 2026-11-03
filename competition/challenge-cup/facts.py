"""申报书和答辩 PPT 共用的事实与数字。

改这里，两份文件一起变。每个数字都要能在仓库代码或下面列出的公开资料里找到；
没有出处的内容写成【待补充：…】，不要估填。最近一次核对：2026-11-01。
"""

TITLE = "哨兵——基于毫米波雷达与协同组网的公路养护作业区智能预警锥桶系统"
SHORT_TITLE = "基于毫米波雷达与协同组网的\n公路养护作业区智能预警锥桶系统"
COMPETITION = "第二十届“挑战杯”全国大学生课外学术科技作品竞赛"
CATEGORY = "科技发明制作类"
SCHOOL = "山东理工大学 交通与车辆工程学院"  # 沿用仓库初稿，提交前请核对

# ---- 与 firmware/common/config.h 一致（tests/test_firmware_consistency.py 检查 Python 侧） ----
TTC1 = 5.0
TTC2 = 2.5
SPEED_LIMIT = 40
OVERSPEED = 1.2
RAIN = 1.4
NIGHT = 1.2
CONFIRM = 3
RELEASE_S = 1.5
REPEAT_MS = 200
MAX_HOPS = 2
LINK_TIMEOUT_S = 3  # 联动锥桶 / 工人端收不到刷新后回到安全状态

# ---- 物料估算（docs/02-物料清单BOM.md） ----
COST_SENTINEL = 115
COST_FOLLOWER = 45
COST_WORKER = 31
COST_GATEWAY = 12
COST_KIT = 350

# ---- 本仓库复现过的验证 ----
# 编译和 Flash 占用是 2026-11-01 的记录。2026-11-03 改过告警状态机和去重后，
# 本环境没有 arduino-cli，没有重编，不要把 Flash 占用写成新结果。
# 单元测试计数是 2026-11-03 在 Python 3.12.3 上 `pytest` 的结果（此前 2026-11-01 为 23 项）。
CORE = "Arduino-ESP32 核心 3.3.12"
FQBN = "esp32:esp32:esp32c3:CDCOnBoot=cdc"
FLASH_USE = "73%～74%"
TESTS = 34

# ---- 外部资料（均已打开核对） ----
FHWA_2024_DEATHS = 850
FHWA_2023_DEATHS = 905
ROAD_KM = "557.89"  # 万公里，2025 年末
RURAL_KM = "471.12"
COUNTY_KM, TOWNSHIP_KM, VILLAGE_KM = "70.57", "124.03", "276.52"
EXPRESSWAY_KM = "19.94"

REFS = [
    (
        "交通运输部. 2025年交通运输行业发展统计公报[EB/OL]. (2026-06-22)",
        "https://xxgk.mot.gov.cn/jigou/zhghs/202606/t20260618_4207752.html",
    ),
    (
        "交通运输部. 关于发布《公路养护安全作业规程》的公告（2015年第16号）[EB/OL]",
        "https://xxgk.mot.gov.cn/jigou/glj/202006/t20200623_3312282.html",
    ),
    (
        "国家质量监督检验检疫总局, 国家标准化管理委员会. 道路交通标志和标线 第4部分：作业区: "
        "GB 5768.4—2017[S]",
        "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=81495E87EE21D71FCC2759945539504F",
    ),
    (
        "中共中央, 国务院. 交通强国建设纲要[Z]. 国务院公报, 2019(28)",
        "https://www.gov.cn/gongbao/content/2019/content_5437132.htm",
    ),
    (
        "交通运输部. 关于推进公路数字化转型 加快智慧公路建设发展的意见: 交公路发〔2023〕131号[Z]",
        "https://xxgk.mot.gov.cn/jigou/glj/202309/t20230920_3922478.html",
    ),
    (
        "应急管理部. 国务院安委会部署开展安全生产治本攻坚三年行动[EB/OL]. (2024-02-05)",
        "https://www.mem.gov.cn/xw/yjglbgzdt/202402/t20240205_477370.shtml",
    ),
    (
        "U.S. Government. 23 CFR 630.1108 Work zone safety management measures and strategies[S]",
        "https://www.ecfr.gov/current/title-23/chapter-I/subchapter-G/part-630/subpart-K/section-630.1108",
    ),
    (
        "Federal Highway Administration. 2026 National Work Zone Awareness Week Fact Sheet: "
        "FHWA-HOP-26-060[R]. 2026",
        "https://ops.fhwa.dot.gov/publications/HOP-26-060_FHWA_NWZAW_Factsheet.pdf",
    ),
    (
        "Federal Highway Administration. EDC-8: Advancing Nighttime Work Zone Safety[EB/OL]",
        "https://www.fhwa.dot.gov/innovation/everydaycounts/edc_8/nighttime_work_zone_safety.cfm",
    ),
    (
        "Gambatese J A, Lee H W, Nnaji C A. Work zone intrusion alert technologies: assessment and "
        "practical guidance: FHWA-OR-RD-17-14[R]. Oregon DOT, 2017",
        "https://rosap.ntl.bts.gov/view/dot/32574",
    ),
    (
        "Hayward J C. Near-miss determination through use of a scale of danger[J]. "
        "Highway Research Record, 1972, 384: 24-34",
        "https://onlinepubs.trb.org/Onlinepubs/hrr/1972/384/384-004.pdf",
    ),
    (
        "Kalman R E. A new approach to linear filtering and prediction problems[J]. "
        "Journal of Basic Engineering, 1960, 82(1): 35-45",
        "https://asmedigitalcollection.asme.org/fluidsengineering/article-abstract/82/1/35/397706/"
        "A-New-Approach-to-Linear-Filtering-and-Prediction",
    ),
    (
        "深圳市海凌科电子有限公司. HLK-LD2451 使用手册 V1.03[Z]. 2024",
        "https://h.hlktech.com/download/HLK-LD2451-24G/1/"
        "HLK-LD2451%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C_V1.03%20.pdf",
    ),
    (
        "深圳市海凌科电子有限公司. LD2451 串口通信协议 V1.03[Z]. 2024",
        "https://h.hlktech.com/download/HLK-LD2451-24G/1/"
        "LD2451%20%E4%B8%B2%E5%8F%A3%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE%20V1.03.pdf",
    ),
    (
        "Espressif Systems. ESP-NOW: ESP-IDF Programming Guide (ESP32-C3)[EB/OL]",
        "https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/network/esp_now.html",
    ),
]


def ref_no(keyword: str) -> int:
    """按关键字找参考文献序号（从 1 开始），找不到就报错，避免正文引用错号。"""
    for index, (text, url) in enumerate(REFS, start=1):
        if keyword in text or keyword in url:
            return index
    raise KeyError(keyword)
