// =============================================================
//  工人报警器固件  (ESP32-C3 + 振动马达 + 蜂鸣器 + 单颗 LED)
//  佩戴在工人背心/手臂上。收到二级预警 → 强震动 + 蜂鸣，提示立即撤离；
//  一级预警 → 短震提醒。按键可“确认/静音” 10 秒。
//  使用前：复制 ../common/config.h 与 protocol.h 到本目录（需 ESP32 Arduino 核心 3.x）
// =============================================================
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "config.h"
#include "protocol.h"

#define NODE_ID      20          // 工人报警器编号 20 起
#define PIN_MOTOR    4           // 振动马达 MOSFET 栅极
#define PIN_BUZZER   3           // 蜂鸣器 MOSFET 栅极
#define PIN_LED      5           // 红色 LED（串 220Ω）
#define PIN_KEY      1           // 按键接 GND，内部上拉
#define PIN_BATT     0

static const uint8_t BCAST[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
volatile uint8_t  rxLevel = LEVEL_SAFE;
volatile uint32_t lastAlertMs = 0;
uint32_t muteUntil = 0, mySeq = 0, lastHeartbeat = 0;

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(AlertPkt)) return;
  const AlertPkt *p = (const AlertPkt*)data;
  if (p->h.magic != PROTO_MAGIC || p->h.type != MSG_ALERT) return;
  if (!(p->mode & MODE_WORKING)) { rxLevel = LEVEL_SAFE; return; }
  rxLevel = p->level; lastAlertMs = millis();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MOTOR, OUTPUT); pinMode(PIN_BUZZER, OUTPUT); pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_KEY, INPUT_PULLUP);
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_now_init();
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BCAST, 6); peer.channel = WIFI_CHANNEL;
  esp_now_add_peer(&peer);
  // 上电短震一下表示正常
  digitalWrite(PIN_MOTOR, HIGH); delay(200); digitalWrite(PIN_MOTOR, LOW);
}

void loop() {
  uint32_t now = millis();
  if (rxLevel > LEVEL_SAFE && now - lastAlertMs > 3000) rxLevel = LEVEL_SAFE;
  if (digitalRead(PIN_KEY) == LOW) muteUntil = now + 10000;   // 静音 10 s（仅声音）

  bool motor = false, buzz = false, led = false;
  if (rxLevel == LEVEL_DANGER) {
    bool on = (now / 120) % 2;
    motor = on; led = on; buzz = on && now > muteUntil;
  } else if (rxLevel == LEVEL_WARN) {
    motor = (now % 1500) < 150;   // 每 1.5 s 短震
    led = (now / 400) % 2;
  }
  digitalWrite(PIN_MOTOR, motor);
  digitalWrite(PIN_BUZZER, buzz);
  digitalWrite(PIN_LED, led);

  if (now - lastHeartbeat > HEARTBEAT_MS) {
    HeartbeatPkt p;
    p.h = {PROTO_MAGIC, PROTO_VERSION, MSG_HEARTBEAT, NODE_ID, NODE_WORKER, ++mySeq};
    p.batt_v = analogReadMilliVolts(PIN_BATT) / 1000.0f * BATT_DIVIDER;
    p.mode = 0; p.level = rxLevel; p.rssi = 0;
    esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
    lastHeartbeat = now;
  }
  delay(5);
}
