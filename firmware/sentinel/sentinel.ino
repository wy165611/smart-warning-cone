// =============================================================
//  哨兵锥桶固件  (ESP32-C3 + HLK-LD2451 + WS2812 + 蜂鸣器 + ASRPRO)
//  功能：雷达测速测距 → 滤波 → TTC 分级预警 → ESP-NOW 广播联动
//        → 语音设置模式 → 心跳/事件上报
//  板卡：Arduino IDE 选 "ESP32C3 Dev Module"，USB CDC On Boot: Enabled
//  依赖库：Adafruit NeoPixel
//  使用前：把 ../common/config.h 和 ../common/protocol.h 复制到本目录
// =============================================================
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "protocol.h"
#include "ld2451.h"
#include "kalman.h"

// ---------- 本节点 ----------
#define NODE_ID      1

// ---------- 引脚（见 docs/03-接线说明.md） ----------
#define PIN_RADAR_RX 6    // 接雷达 TX
#define PIN_RADAR_TX 7    // 接雷达 RX
#define PIN_ASR_RX   20   // 接 ASRPRO TX
#define PIN_ASR_TX   21   // 接 ASRPRO RX
#define PIN_LED      10   // WS2812 DIN（串 330Ω）
#define PIN_BUZZER   3    // MOSFET 栅极
#define PIN_BATT     0    // 分压后电池电压（ADC1_CH0）

// 使用核心预定义的串口对象，避免重复构造同一 UART
// （需在 Arduino IDE 中开启 USB CDC On Boot，使 Serial 走 USB，Serial0 才空闲）
HardwareSerial &RadarSerial = Serial1;   // UART1
HardwareSerial &AsrSerial   = Serial0;   // UART0
Adafruit_NeoPixel strip(LED_NUM, PIN_LED, NEO_GRB + NEO_KHZ800);
LD2451 radar;
Kalman1D kfDist(0.5f, 4.0f), kfSpeed(0.5f, 4.0f);

static const uint8_t BCAST[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};

uint32_t seq = 0;
uint8_t  mode = MODE_WORKING;       // 上电默认作业中、右侧封道
uint8_t  level = LEVEL_SAFE;
int      confirmCnt = 0;
uint32_t lastHitMs = 0, lastAlertTx = 0, lastHeartbeat = 0;
uint8_t  lastSentLevel = 255;

// 当前事件统计（一辆车从出现到离开为一次事件）
bool     inEvent = false;
uint32_t eventStart = 0;
uint8_t  evMaxLevel = 0;
float    evMaxSpeed = 0, evMinTtc = 99, evMinDist = 999;

float filtDist = 0, filtSpeed = 0, curTtc = 99;

// -------------------------------------------------------------
float readBattery() {
  uint32_t mv = analogReadMilliVolts(PIN_BATT);
  return mv / 1000.0f * BATT_DIVIDER;
}

void fillHeader(PktHeader &h, uint8_t type) {
  h.magic = PROTO_MAGIC; h.version = PROTO_VERSION; h.type = type;
  h.node_id = NODE_ID; h.node_type = NODE_SENTINEL; h.seq = ++seq;
}

void sendAlert() {
  AlertPkt p; fillHeader(p.h, MSG_ALERT);
  p.level = level; p.mode = mode; p.speed_kmh = filtSpeed;
  p.dist_m = filtDist; p.ttc_s = curTtc; p.hops = 0;
  esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
}

void sendConfig() {
  ConfigPkt p; fillHeader(p.h, MSG_CONFIG); p.mode = mode;
  for (int i = 0; i < 3; i++) {             // 重发 3 次保证收到
    esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
    delay(20);
  }
}

void sendHeartbeat() {
  HeartbeatPkt p; fillHeader(p.h, MSG_HEARTBEAT);
  p.batt_v = readBattery(); p.mode = mode; p.level = level; p.rssi = 0;
  esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
}

void sendEvent() {
  EventPkt p; fillHeader(p.h, MSG_EVENT);
  p.max_level = evMaxLevel; p.max_speed = evMaxSpeed;
  p.min_ttc = evMinTtc; p.min_dist = evMinDist;
  p.duration_ms = millis() - eventStart;
  esp_now_send(BCAST, (uint8_t*)&p, sizeof(p));
}

// -------------------------------------------------------------
// 灯光与声音：非阻塞闪烁
void renderOutput() {
  static uint32_t last = 0; static bool on = false;
  uint32_t period;
  uint32_t color;
  if (!(mode & MODE_WORKING)) {            // 非作业：暗黄常亮，省电
    strip.fill(strip.Color(60, 40, 0)); strip.show();
    digitalWrite(PIN_BUZZER, LOW); return;
  }
  switch (level) {
    case LEVEL_DANGER: period = 70;  color = strip.Color(255, 0, 0);   break;
    case LEVEL_WARN:   period = 220; color = strip.Color(255, 50, 0);  break;
    default:           period = 800; color = strip.Color(255, 150, 0); break;
  }
  if (millis() - last < period) return;
  last = millis(); on = !on;

  if (level == LEVEL_WARN) {
    // 一级：红黄交替
    for (int i = 0; i < LED_NUM; i++)
      strip.setPixelColor(i, ((i / 5) % 2 == on) ? color : strip.Color(255,150,0));
  } else {
    strip.fill(on ? color : 0);
  }
  strip.show();
  digitalWrite(PIN_BUZZER, (level == LEVEL_DANGER && on) ? HIGH : LOW);
}

// -------------------------------------------------------------
// 根据模式得到当前阈值（自适应阈值）
void currentThresholds(float &t1, float &t2) {
  float k = 1.0f;
  if (mode & MODE_RAIN)  k *= RAIN_FACTOR;
  if (mode & MODE_NIGHT) k *= NIGHT_FACTOR;
  t1 = TTC_LEVEL1_S * k;
  t2 = TTC_LEVEL2_S * k;
}

void processRadar() {
  RadarFrame f;
  while (radar.poll(f)) {
    // 选“最危险”的接近目标：TTC 最小者
    bool found = false; float bestTtc = 99, bestD = 0, bestV = 0;
    for (int i = 0; i < f.count; i++) {
      const RadarTarget &t = f.targets[i];
      if (!t.approaching) continue;
      if (t.speed_kmh < MIN_TRACK_SPEED || t.dist_m > MAX_TRACK_DIST) continue;
      float ttc = t.dist_m / (t.speed_kmh / 3.6f);
      if (ttc < bestTtc) { bestTtc = ttc; bestD = t.dist_m; bestV = t.speed_kmh; found = true; }
    }

    if (!found) {
      if (millis() - lastHitMs > RELEASE_MS) {
        confirmCnt = 0; level = LEVEL_SAFE; curTtc = 99;
        kfDist.reset(); kfSpeed.reset();
        if (inEvent) { sendEvent(); inEvent = false; }
      }
      continue;
    }

    lastHitMs = millis();
    filtDist  = kfDist.update(bestD);
    filtSpeed = kfSpeed.update(bestV);
    curTtc    = (filtSpeed > 1) ? filtDist / (filtSpeed / 3.6f) : 99;

    float t1, t2; currentThresholds(t1, t2);
    uint8_t want = LEVEL_SAFE;
    if (curTtc < t2) want = LEVEL_DANGER;
    else if (curTtc < t1 || filtSpeed > SPEED_LIMIT_KMH * OVERSPEED_RATIO) want = LEVEL_WARN;

    if (want > LEVEL_SAFE) confirmCnt++; else confirmCnt = 0;
    // 升级需连续确认；降级立即（但有 RELEASE_MS 保持）
    if (confirmCnt >= CONFIRM_FRAMES || want < level) level = want;

    // 事件统计
    if (!inEvent) {
      inEvent = true; eventStart = millis();
      evMaxLevel = 0; evMaxSpeed = 0; evMinTtc = 99; evMinDist = 999;
    }
    if (level > evMaxLevel) evMaxLevel = level;
    if (filtSpeed > evMaxSpeed) evMaxSpeed = filtSpeed;
    if (curTtc < evMinTtc) evMinTtc = curTtc;
    if (filtDist < evMinDist) evMinDist = filtDist;

    Serial.printf("[RADAR] d=%.1fm v=%.1fkm/h ttc=%.2fs level=%u\n",
                  filtDist, filtSpeed, curTtc, level);
  }
  if (!(mode & MODE_WORKING)) level = LEVEL_SAFE;
}

// -------------------------------------------------------------
// 语音串口：0xAA 0x55 CMD SUM
void replyVoice(uint8_t code) {
  uint8_t b[4] = {VOICE_HDR1, VOICE_HDR2, code, (uint8_t)(VOICE_HDR1 + VOICE_HDR2 + code)};
  AsrSerial.write(b, 4);
}

void selfTest() {
  for (int k = 0; k < 3; k++) {
    strip.fill(strip.Color(255, 0, 0)); strip.show(); digitalWrite(PIN_BUZZER, HIGH); delay(150);
    strip.fill(0); strip.show(); digitalWrite(PIN_BUZZER, LOW); delay(150);
  }
}

void handleVoice(uint8_t cmd) {
  Serial.printf("[VOICE] cmd=0x%02X\n", cmd);
  switch (cmd) {
    case VC_START_WORK: mode |= MODE_WORKING;  break;
    case VC_STOP_WORK:  mode &= ~MODE_WORKING; break;
    case VC_LEFT:       mode |= MODE_LEFT;     break;
    case VC_RIGHT:      mode &= ~MODE_LEFT;    break;
    case VC_RAIN_ON:    mode |= MODE_RAIN;     break;
    case VC_RAIN_OFF:   mode &= ~MODE_RAIN;    break;
    case VC_NIGHT_ON:   mode |= MODE_NIGHT;    break;
    case VC_NIGHT_OFF:  mode &= ~MODE_NIGHT;   break;
    case VC_BATTERY:
      replyVoice(readBattery() > BATT_LOW_V ? VOICE_REPLY_BATT_OK : VOICE_REPLY_BATT_LOW);
      return;
    case VC_TEST:       selfTest(); return;
    default: return;
  }
  sendConfig();
}

void pollVoice() {
  static uint8_t buf[4]; static int idx = 0;
  while (AsrSerial.available()) {
    uint8_t c = AsrSerial.read();
    if (idx == 0 && c != VOICE_HDR1) continue;
    if (idx == 1 && c != VOICE_HDR2) { idx = (c == VOICE_HDR1) ? 1 : 0; continue; }
    buf[idx++] = c;
    if (idx == 4) {
      idx = 0;
      if ((uint8_t)(buf[0] + buf[1] + buf[2]) == buf[3]) handleVoice(buf[2]);
    }
  }
}

// -------------------------------------------------------------
void setup() {
  Serial.begin(115200);                       // USB CDC 日志
  seq = esp_random() & 0x00FFFFFF;            // 随机起始序号：重启后接收方不会误判为旧包
  RadarSerial.begin(115200, SERIAL_8N1, PIN_RADAR_RX, PIN_RADAR_TX);
  AsrSerial.begin(9600, SERIAL_8N1, PIN_ASR_RX, PIN_ASR_TX);
  radar.begin(&RadarSerial);

  pinMode(PIN_BUZZER, OUTPUT);
  analogReadResolution(12);
  strip.begin(); strip.setBrightness(LED_BRIGHTNESS); strip.show();

  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) { Serial.println("ESP-NOW init failed"); }
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BCAST, 6);
  peer.channel = WIFI_CHANNEL; peer.encrypt = false;
  esp_now_add_peer(&peer);

  Serial.printf("Sentinel #%d ready, MAC %s\n", NODE_ID, WiFi.macAddress().c_str());
  selfTest();
  sendConfig();
}

void loop() {
  processRadar();
  pollVoice();

  // 等级变化立即广播，告警中周期重发
  if (level != lastSentLevel || (level > LEVEL_SAFE && millis() - lastAlertTx > ALERT_REPEAT_MS)) {
    sendAlert(); lastSentLevel = level; lastAlertTx = millis();
  }
  if (millis() - lastHeartbeat > HEARTBEAT_MS) { sendHeartbeat(); lastHeartbeat = millis(); }

  renderOutput();
}
