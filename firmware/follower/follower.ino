// =============================================================
//  联动锥桶固件  (ESP32-C3 + WS2812 + 蜂鸣器)
//  接收哨兵的 ESP-NOW 预警 → 按自身编号延时点亮，形成流水灯引导变道
//  多跳中继：收到新序号的预警包后转发一次（hops+1，最多 2 跳）；
//            模式配置包按序号去重后也转发一次，远处锥桶同样能切换模式
//  config.h / protocol.h 是 ../common/ 的副本；每块板烧录前修改 NODE_ID
// =============================================================
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "protocol.h"

#define NODE_ID      2          // 联动锥桶编号：2、3、4…（从哨兵往作业区方向递增）
#define POSITION     (NODE_ID - 1)   // 距哨兵第几个
#define MAX_HOPS     2

#define PIN_LED      10
#define PIN_BUZZER   3
#define PIN_BATT     0

Adafruit_NeoPixel strip(LED_NUM, PIN_LED, NEO_GRB + NEO_KHZ800);
static const uint8_t BCAST[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};

volatile uint8_t  rxLevel = LEVEL_SAFE;
volatile uint8_t  rxMode = MODE_WORKING;
volatile uint32_t rxAt = 0;          // 进入预警的时刻（流水灯相位基准）
volatile uint32_t lastAlertMs = 0;   // 最近一次收到预警包
uint32_t lastSeqFrom[256];           // 按发送者 node_id（0–255）去重，避免 16 号以后互相覆盖
uint8_t  seqSeen[256];               // 0 = 尚未收到该节点。收到之后才按 lastSeq 去重，序号 0 的第一包会保留
uint32_t mySeq = 0, lastHeartbeat = 0;
int8_t   lastRssi = 0;
// 回调在 Wi-Fi 任务里，loop 在另一个任务。中继包放进队列再发，避免两个任务同时改同一块结构体。
QueueHandle_t alertQ;
QueueHandle_t configQ;

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len < (int)sizeof(PktHeader)) return;
  const PktHeader *h = (const PktHeader*)data;
  if (h->magic != PROTO_MAGIC || h->node_id == NODE_ID) return;
  if (info && info->rx_ctrl) lastRssi = info->rx_ctrl->rssi;

  if (h->type == MSG_ALERT && len == sizeof(AlertPkt)) {
    const AlertPkt *p = (const AlertPkt*)data;
    if (!seqIsNew(seqSeen, lastSeqFrom, h->node_id, h->seq)) return;
    // 先写模式再写等级：结束作业的包即使还带着旧等级，也不会被渲染成报警。
    // 非作业或安全等级都把等级清掉，避免下次“开始作业”时沿用上一次的二级。
    rxMode = p->mode;
    if (!(p->mode & MODE_WORKING) || p->level == LEVEL_SAFE) {
      rxLevel = LEVEL_SAFE;
    } else {
      if (rxLevel == LEVEL_SAFE) rxAt = millis();
      rxLevel = p->level;
    }
    lastAlertMs = millis();
    if (p->hops < MAX_HOPS && alertQ) {
      AlertPkt copy = *p;
      copy.hops++;
      xQueueSend(alertQ, &copy, 0);
    }
  } else if (h->type == MSG_CONFIG && len == sizeof(ConfigPkt)) {
    // 哨兵把同一个配置包（同一序号）连发 3 次，去重后只处理、转发一次。
    // 每个节点对同一序号只转发一次，所以不需要跳数也不会无限循环。
    if (!seqIsNew(seqSeen, lastSeqFrom, h->node_id, h->seq)) return;
    const ConfigPkt *c = (const ConfigPkt*)data;
    rxMode = c->mode;
    if (!(c->mode & MODE_WORKING)) rxLevel = LEVEL_SAFE;
    if (configQ) xQueueSend(configQ, c, 0);
  }
}

// 流水灯：一级预警时，灯光从哨兵向作业区方向“流动”
// 本节点在 POSITION*FLOW_STEP_MS 后进入点亮相位，所有节点同周期，
// 视觉上就是一个光点沿锥桶阵列移动，指示车辆向一侧变道。
void render() {
  // WS2812 的 show() 会关中断约 1 ms。每圈都刷，ESP32-C3 上容易挤占 Wi-Fi。
  // 20 ms 一帧足够跟上 70 ms 爆闪和 120 ms 流水。
  static uint32_t lastDraw = 0;
  uint32_t now = millis();
  if (now - lastDraw < 20) return;
  lastDraw = now;
  uint8_t lv = rxLevel; uint8_t md = rxMode;
  if (!(md & MODE_WORKING)) { strip.fill(strip.Color(60,40,0)); strip.show(); digitalWrite(PIN_BUZZER, LOW); return; }

  if (lv == LEVEL_SAFE) {
    bool on = (now / 800) % 2;
    strip.fill(on ? strip.Color(255,150,0) : 0);
    digitalWrite(PIN_BUZZER, LOW);
  } else if (lv == LEVEL_WARN) {
    const uint32_t cycle = FLOW_STEP_MS * 8;           // 一轮流动周期
    uint32_t t = (now - rxAt + cycle - (POSITION * FLOW_STEP_MS) % cycle) % cycle;
    bool on = t < FLOW_STEP_MS * 2;
    // 灯带内部也做方向箭头：左侧封道从右往左点亮，反之亦然
    int lit = on ? map(t, 0, FLOW_STEP_MS * 2, 0, LED_NUM) : 0;
    strip.clear();
    for (int i = 0; i < lit; i++) {
      int px = (md & MODE_LEFT) ? (LED_NUM - 1 - i) : i;
      strip.setPixelColor(px, strip.Color(255, 40, 0));
    }
    digitalWrite(PIN_BUZZER, LOW);
  } else {
    bool on = (now / 70) % 2;
    strip.fill(on ? strip.Color(255,0,0) : 0);
    digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
  }
  strip.show();
}

void setup() {
  Serial.begin(115200);
  mySeq = esp_random() & 0x00FFFFFF;
  pinMode(PIN_BUZZER, OUTPUT);
  strip.begin(); strip.setBrightness(LED_BRIGHTNESS); strip.show();

  WiFi.mode(WIFI_STA);
  alertQ = xQueueCreate(4, sizeof(AlertPkt));
  configQ = xQueueCreate(2, sizeof(ConfigPkt));
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_now_init();
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BCAST, 6); peer.channel = WIFI_CHANNEL;
  esp_now_add_peer(&peer);
  Serial.printf("Follower #%d ready\n", NODE_ID);
}

void loop() {
  bool backedOff = false;
  AlertPkt alert;
  if (alertQ && xQueueReceive(alertQ, &alert, 0) == pdTRUE) {
    delay(random(2, 15));                       // 随机退避，减少冲突
    backedOff = true;
    esp_now_send(BCAST, (uint8_t*)&alert, sizeof(alert));
  }
  ConfigPkt cfg;
  if (configQ && xQueueReceive(configQ, &cfg, 0) == pdTRUE) {
    if (!backedOff) delay(random(2, 15));
    esp_now_send(BCAST, (uint8_t*)&cfg, sizeof(cfg));
  }
  // 哨兵掉线保护：LINK_LOSS_MS 内没收到告警刷新，则回到安全状态
  if (rxLevel > LEVEL_SAFE && millis() - lastAlertMs > LINK_LOSS_MS) rxLevel = LEVEL_SAFE;
  if (millis() - lastHeartbeat > HEARTBEAT_MS) {
    HeartbeatPkt p;
    p.h = {PROTO_MAGIC, PROTO_VERSION, MSG_HEARTBEAT, NODE_ID, NODE_FOLLOWER, ++mySeq};
    p.batt_v = analogReadMilliVolts(PIN_BATT) / 1000.0f * BATT_DIVIDER;
    p.mode = rxMode; p.level = rxLevel; p.rssi = lastRssi;
    esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
    lastHeartbeat = millis();
  }
  render();
}
