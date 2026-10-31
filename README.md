# 哨兵 · 公路养护作业区智能预警锥桶系统

> Sentinel Cone — a low-cost, radar-based active warning system for highway maintenance work zones.

用百元级智能锥桶，把传统“被动隔离”的作业区升级为“**主动感知 → 分级预警 → 协同联动 → 数据上云**”的智慧作业区，服务公路养护安全生产与公路数字化转型。

```
来车 ──► [哨兵锥桶 #1 · 毫米波雷达测速测距] ──► TTC 分级预警（灯光 + 声响）
                  │ ESP-NOW 广播
                  ▼
        [联动锥桶 #2] ─► [联动锥桶 #3] ─► …   流水灯引导车辆提前变道
                  │
        [工人报警器] 震动 + 声光，提示撤离
                  │
        [网关] ESP-NOW → Wi-Fi → MQTT
                  ▼
        [服务器 + 网页看板] 实时状态 · 超速统计 · 危险接近事件 · 安全报告
```

## 仓库结构

| 目录 | 内容 |
|---|---|
| `docs/01-申报书.md` | 比赛申报书完整稿（可直接改成 Word） |
| `docs/02-物料清单BOM.md` | 全部器件、数量、参考价、购买关键词 |
| `docs/03-接线说明.md` | 四种节点的逐线接线表与接线图 |
| `docs/04-从零开始搭建指南.md` | 环境安装 → 烧录 → 联调 → 上云，一步一步 |
| `docs/05-算法说明.md` | 滤波、TTC、分级预警、自适应阈值、防误报 |
| `docs/06-通信协议.md` | 雷达串口协议、ESP-NOW 数据包、语音串口协议、MQTT 主题 |
| `docs/07-测试方案与数据记录表.md` | 精度、提前量、误报率、续航测试方法与表格 |
| `docs/08-演示与答辩脚本.md` | 现场演示流程、视频分镜、答辩常见问题 |
| `docs/09-PCB与外壳设计.md` | 嘉立创 EDA 画板要点、外壳与安装方式 |
| `firmware/common/` | 所有节点共用的协议与配置头文件 |
| `firmware/sentinel/` | 哨兵锥桶固件（雷达 + 预警 + 广播） |
| `firmware/follower/` | 联动锥桶固件（接收 + 流水灯） |
| `firmware/worker/` | 工人报警器固件（震动 + 蜂鸣） |
| `firmware/gateway/` | 网关固件（ESP-NOW 转 MQTT） |
| `asrpro/` | ASRPRO 语音模块程序与命令词表 |
| `server/` | Python 后端（MQTT 入库 + API）与网页看板 |
| `tools/` | 无硬件模拟器、雷达串口调试工具 |

## 快速开始

1. 按 `docs/02-物料清单BOM.md` 买料。
2. 按 `docs/04-从零开始搭建指南.md` 安装 Arduino IDE + ESP32 支持包 + 库。
3. 修改 `firmware/common/config.h` 里的 Wi-Fi 信道、节点编号。
4. 依次烧录 `sentinel`、`follower`、`worker`、`gateway`。
5. 运行 `server/`（`docker compose up` 或 `python app.py`），浏览器打开 `http://localhost:8000`。
6. 没有硬件时，先运行 `tools/simulator.py` 看看网页效果。

## 关键参数（默认值，可在 config.h 修改）

| 参数 | 默认 | 说明 |
|---|---|---|
| 一级预警 TTC | 5.0 s | 或超限速 20% |
| 二级预警 TTC | 2.5 s | 触发工人报警 |
| 作业区限速 | 40 km/h | 按现场标志设置 |
| 连续确认帧 | 3 帧 | 防误报 |
| 雷达 | HLK-LD2451 | 24GHz FMCW，最远约 100 m，水平 ±15° |

## 安全声明

所有实测请在**封闭场地、低速**条件下进行，不得在开放道路上用真实车辆冲撞测试。本项目为教学与竞赛原型，不能替代国家标准规定的作业区交通安全设施。

## License

MIT
