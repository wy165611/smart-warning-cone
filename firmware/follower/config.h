// =============================================================
//  哨兵锥桶系统 · 全局配置
//  所有节点共用。把本文件和 protocol.h 复制到每个 .ino 同目录下
//  （Arduino IDE 只编译草图目录内的文件）。
// =============================================================
#pragma once

// ---------- 无线 ----------
// ESP-NOW 与 Wi-Fi 必须在同一信道。网关要连路由器，
// 所以这里填路由器的 2.4G 信道（路由器后台设为固定信道，如 1/6/11）。
#define WIFI_CHANNEL        6

// 网关连接的 Wi-Fi 与 MQTT（仅 gateway 使用）
#define WIFI_SSID           "YourWiFi"
#define WIFI_PASS           "YourPassword"
#define MQTT_HOST           "192.168.1.100"   // 运行 server 的电脑 IP
#define MQTT_PORT           1883
#define MQTT_TOPIC_PREFIX   "cone"            // cone/<node_id>/alert 等

// ---------- 作业区参数 ----------
#define SPEED_LIMIT_KMH     40.0f   // 作业区限速
#define OVERSPEED_RATIO     1.2f    // 超限速 20% 触发一级
#define TTC_LEVEL1_S        5.0f    // 一级预警阈值
#define TTC_LEVEL2_S        2.5f    // 二级预警阈值
#define RAIN_FACTOR         1.4f    // 雨天模式：阈值放大倍数（制动距离变长）
#define NIGHT_FACTOR        1.2f    // 夜间模式：阈值放大倍数
#define CONFIRM_FRAMES      3       // 连续 N 帧满足才触发
#define RELEASE_MS          1500    // 目标消失后保持告警的时间
#define MIN_TRACK_SPEED     5       // 低于此速度（km/h）的目标忽略
#define MAX_TRACK_DIST      100     // 关注的最远距离（m）

// ---------- 联动 ----------
#define FLOW_STEP_MS        120     // 流水灯：每个锥桶比前一个延迟多少 ms
#define ALERT_REPEAT_MS     200     // 告警期间重复广播间隔
#define HEARTBEAT_MS        5000    // 心跳间隔（上报电量/在线）
#define LINK_LOSS_MS        3000    // 联动锥桶 / 工人端收不到预警刷新后回到安全

// ---------- 灯带 ----------
#define LED_NUM             30
#define LED_BRIGHTNESS      180     // 0-255，户外白天建议 180 以上

// ---------- 电池 ----------
// 18650 经 100k/100k 分压后接 ADC：电池电压 = 读数电压 × 2
#define BATT_DIVIDER        2.0f
#define BATT_LOW_V          3.4f
