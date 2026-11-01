// =============================================================
//  哨兵锥桶系统 · 通信协议定义（ESP-NOW 数据包 + 语音串口命令）
//  详细说明见 docs/06-通信协议.md
// =============================================================
#pragma once
#include <stdint.h>

#define PROTO_MAGIC   0x5C   // 包头魔数，过滤其他 ESP-NOW 设备
#define PROTO_VERSION 1

// ---------- 节点类型 ----------
enum NodeType : uint8_t {
  NODE_SENTINEL = 1,   // 哨兵（带雷达）
  NODE_FOLLOWER = 2,   // 联动锥桶
  NODE_WORKER   = 3,   // 工人报警器
  NODE_GATEWAY  = 4    // 网关
};

// ---------- 预警等级 ----------
enum AlertLevel : uint8_t {
  LEVEL_SAFE   = 0,    // 安全：黄灯慢闪
  LEVEL_WARN   = 1,    // 一级：红黄快闪 + 流水灯
  LEVEL_DANGER = 2     // 二级：红色爆闪 + 蜂鸣 + 工人震动
};

// ---------- 消息类型 ----------
enum MsgType : uint8_t {
  MSG_ALERT     = 1,   // 哨兵 → 全体：预警
  MSG_HEARTBEAT = 2,   // 任意 → 网关：在线/电量
  MSG_CONFIG    = 3,   // 哨兵 → 全体：模式切换（来自语音，联动锥桶去重后转发一次）
  MSG_EVENT     = 4    // 哨兵 → 网关：一次完整的危险接近事件
};

// ---------- 工作模式（位标志） ----------
#define MODE_WORKING   0x01   // 作业中（未开启则只慢闪不报警）
#define MODE_LEFT      0x02   // 左侧封道（流水灯向左）；未置位为右侧封道
#define MODE_RAIN      0x04   // 雨天模式
#define MODE_NIGHT     0x08   // 夜间模式

#pragma pack(push, 1)
typedef struct {
  uint8_t  magic;      // PROTO_MAGIC
  uint8_t  version;    // PROTO_VERSION
  uint8_t  type;       // MsgType
  uint8_t  node_id;    // 发送者编号
  uint8_t  node_type;  // NodeType
  uint32_t seq;        // 序号，接收方据此去重
} PktHeader;

typedef struct {
  PktHeader h;
  uint8_t  level;      // AlertLevel
  uint8_t  mode;       // 当前模式位
  float    speed_kmh;  // 目标速度
  float    dist_m;     // 目标距离
  float    ttc_s;      // 碰撞时间
  uint8_t  hops;       // 已转发次数（多跳中继，最多 2）
} AlertPkt;

typedef struct {
  PktHeader h;
  float    batt_v;     // 电池电压
  uint8_t  mode;
  uint8_t  level;
  int8_t   rssi;       // 最近一次收到包的信号强度
} HeartbeatPkt;

typedef struct {
  PktHeader h;
  uint8_t  mode;       // 新模式
} ConfigPkt;

typedef struct {
  PktHeader h;
  uint8_t  max_level;  // 本次事件最高等级
  float    max_speed;  // 最高速度
  float    min_ttc;    // 最小 TTC
  float    min_dist;   // 最近距离
  uint32_t duration_ms;
} EventPkt;
#pragma pack(pop)

// ---------- ASRPRO → 哨兵 串口命令 ----------
// 帧格式：0xAA 0x55 CMD (0xAA+0x55+CMD)&0xFF   共 4 字节，9600 8N1
#define VOICE_HDR1 0xAA
#define VOICE_HDR2 0x55
enum VoiceCmd : uint8_t {
  VC_START_WORK = 0x01,  // 开始作业
  VC_STOP_WORK  = 0x02,  // 结束作业
  VC_LEFT       = 0x03,  // 左侧封道
  VC_RIGHT      = 0x04,  // 右侧封道
  VC_RAIN_ON    = 0x05,  // 雨天模式
  VC_RAIN_OFF   = 0x06,  // 关闭雨天模式
  VC_NIGHT_ON   = 0x07,  // 夜间模式
  VC_NIGHT_OFF  = 0x08,  // 关闭夜间模式
  VC_BATTERY    = 0x09,  // 报告电量
  VC_TEST       = 0x0A   // 哨兵本机自检（红灯+蜂鸣闪 3 次）
};
// 哨兵 → ASRPRO 回复（用于播报）：0xAA 0x55 0x80|状态 校验
#define VOICE_REPLY_BATT_OK   0x81
#define VOICE_REPLY_BATT_LOW  0x82
