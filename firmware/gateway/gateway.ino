// =============================================================
//  网关固件  (ESP32 / ESP32-C3 / ESP32-S3 均可)
//  ESP-NOW 收全部节点数据 → Wi-Fi → MQTT 发布 JSON
//  主题：
//    cone/<id>/alert      预警（等级、速度、距离、TTC）
//    cone/<id>/heartbeat  心跳（电量、模式、RSSI）
//    cone/<id>/event      一次完整危险接近事件
//    cone/<id>/config     模式变化
//  注意：路由器 2.4G 信道必须固定为 config.h 中的 WIFI_CHANNEL
//  依赖库：PubSubClient (Nick O'Leary)
// =============================================================
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <PubSubClient.h>
#include "config.h"
#include "protocol.h"

WiFiClient   net;
PubSubClient mqtt(net);

// ESP-NOW 回调在 Wi-Fi 任务里，不能直接发 MQTT，先放入队列
struct RxItem { uint8_t len; uint8_t data[64]; };
QueueHandle_t rxQueue;

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len < (int)sizeof(PktHeader) || len > 64) return;
  if (((const PktHeader*)data)->magic != PROTO_MAGIC) return;
  RxItem it; it.len = len; memcpy(it.data, data, len);
  xQueueSend(rxQueue, &it, 0);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.printf("\nIP %s  channel %d\n", WiFi.localIP().toString().c_str(), WiFi.channel());
  if (WiFi.channel() != WIFI_CHANNEL)
    Serial.println("!! 路由器信道与 WIFI_CHANNEL 不一致，锥桶将收不到/发不到，请固定路由器信道");
}

void connectMqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  while (!mqtt.connected()) {
    String cid = "cone-gw-" + WiFi.macAddress();
    if (mqtt.connect(cid.c_str())) Serial.println("MQTT connected");
    else { Serial.printf("MQTT fail rc=%d\n", mqtt.state()); delay(2000); }
  }
}

void publish(uint8_t id, const char *sub, const String &json) {
  char topic[48];
  snprintf(topic, sizeof(topic), "%s/%u/%s", MQTT_TOPIC_PREFIX, id, sub);
  mqtt.publish(topic, json.c_str());
  Serial.printf("%s %s\n", topic, json.c_str());
}

void handle(const RxItem &it) {
  const PktHeader *h = (const PktHeader*)it.data;
  char b[200];
  switch (h->type) {
    case MSG_ALERT: if (it.len == sizeof(AlertPkt)) {
      const AlertPkt *p = (const AlertPkt*)it.data;
      if (p->hops != 0) return;   // 只上报哨兵原始包，忽略中继副本
      snprintf(b, sizeof(b), "{\"level\":%u,\"mode\":%u,\"speed\":%.1f,\"dist\":%.1f,\"ttc\":%.2f,\"seq\":%lu}",
               p->level, p->mode, p->speed_kmh, p->dist_m, p->ttc_s, (unsigned long)h->seq);
      publish(h->node_id, "alert", b);
    } break;
    case MSG_HEARTBEAT: if (it.len == sizeof(HeartbeatPkt)) {
      const HeartbeatPkt *p = (const HeartbeatPkt*)it.data;
      snprintf(b, sizeof(b), "{\"type\":%u,\"batt\":%.2f,\"mode\":%u,\"level\":%u,\"rssi\":%d}",
               h->node_type, p->batt_v, p->mode, p->level, p->rssi);
      publish(h->node_id, "heartbeat", b);
    } break;
    case MSG_EVENT: if (it.len == sizeof(EventPkt)) {
      const EventPkt *p = (const EventPkt*)it.data;
      snprintf(b, sizeof(b), "{\"max_level\":%u,\"max_speed\":%.1f,\"min_ttc\":%.2f,\"min_dist\":%.1f,\"duration_ms\":%lu}",
               p->max_level, p->max_speed, p->min_ttc, p->min_dist, (unsigned long)p->duration_ms);
      publish(h->node_id, "event", b);
    } break;
    case MSG_CONFIG: if (it.len == sizeof(ConfigPkt)) {
      snprintf(b, sizeof(b), "{\"mode\":%u}", ((const ConfigPkt*)it.data)->mode);
      publish(h->node_id, "config", b);
    } break;
  }
}

void setup() {
  Serial.begin(115200);
  rxQueue = xQueueCreate(32, sizeof(RxItem));
  connectWiFi();
  esp_now_init();
  esp_now_register_recv_cb(onRecv);
  connectMqtt();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  RxItem it;
  while (xQueueReceive(rxQueue, &it, 0) == pdTRUE) handle(it);
}
