// =============================================================
//  联动锥桶固件  (ESP32-C3 + WS2812 + 蜂鸣器)
//  接收哨兵的 ESP-NOW 预警 → 按自身编号延时点亮，形成流水灯引导变道
//  多跳中继：收到新序号的包后转发一次（hops+1，最多 2 跳）
//  使用前：复制 ../common/config.h 与 protocol.h 到本目录，修改 NODE_ID
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
volatile bool     needRelay = false;
AlertPkt relayPkt;
uint32_t lastSeqFrom[256];           // 按发送者 node_id（0–255）去重，避免 16 号以后互相覆盖
uint8_t  seqSeen[256];               // 0 = 还没收到过该节点；否则序号 0 会被当成“已经见过”
uint32_t mySeq = 0, lastHeartbeat = 0;
int8_t   lastRssi = 0;

// 去重：同一发送者的序号必须变大；若序号“倒退”很多，说明对方重启过，也接受
bool isNew(uint8_t id, uint32_t seq) {
  uint32_t last = lastSeqFrom[id];
  if (seqSeen[id]) {
    if (seq == last) return false;
    if (seq < last && last - seq < 64) return false;   // 中继副本或乱序旧包
  }
  lastSeqFrom[id] = seq;
  seqSeen[id] = 1;
  return true;
}

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len < (int)sizeof(PktHeader)) return;
  const PktHeader *h = (const PktHeader*)data;
  if (h->magic != PROTO_MAGIC || h->node_id == NODE_ID) return;
  if (info && info->rx_ctrl) lastRssi = info->rx_ctrl->rssi;

  if (h->type == MSG_ALERT && len == sizeof(AlertPkt)) {
    const AlertPkt *p = (const AlertPkt*)data;
    if (!isNew(h->node_id, h->seq)) return;
    if (p->level != rxLevel || p->level > LEVEL_SAFE) {
      if (rxLevel == LEVEL_SAFE && p->level > LEVEL_SAFE) rxAt = millis();
      rxLevel = p->level;
    }
    rxMode = p->mode;
    lastAlertMs = millis();
    if (p->hops < MAX_HOPS) { relayPkt = *p; relayPkt.hops++; needRelay = true; }
  } else if (h->type == MSG_CONFIG && len == sizeof(ConfigPkt)) {
    rxMode = ((const ConfigPkt*)data)->mode;
  }
}

// 流水灯：一级预警时，灯光从哨兵向作业区方向“流动”
// 本节点在 POSITION*FLOW_STEP_MS 后进入点亮相位，所有节点同周期，
// 视觉上就是一个光点沿锥桶阵列移动，指示车辆向一侧变道。
void render() {
  uint8_t lv = rxLevel; uint8_t md = rxMode;
  uint32_t now = millis();
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
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_now_init();
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BCAST, 6); peer.channel = WIFI_CHANNEL;
  esp_now_add_peer(&peer);
  Serial.printf("Follower #%d ready\n", NODE_ID);
}

void loop() {
  if (needRelay) {
    needRelay = false;
    delay(random(2, 15));                       // 随机退避，减少冲突
    esp_now_send(BCAST, (uint8_t*)&relayPkt, sizeof(relayPkt));
  }
  // 哨兵掉线保护：3 秒没收到告警刷新，则回到安全状态
  if (rxLevel > LEVEL_SAFE && millis() - lastAlertMs > 3000) rxLevel = LEVEL_SAFE;
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
