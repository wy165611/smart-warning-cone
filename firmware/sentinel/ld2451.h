// =============================================================
//  HLK-LD2451 24GHz 车辆雷达 串口解析
//  依据：海凌科《LD2451 串口通信协议 V1.03》
//  数据帧：F4 F3 F2 F1 | 长度(2B,小端) | 目标数(1B) 报警(1B)
//          | 每个目标 5B：角度(-0x80) 距离(m) 方向(1=靠近) 速度(km/h) 信噪比
//          | F8 F7 F6 F5
//  无目标时帧内数据为 00 00。默认 115200 8N1，有目标 ~100ms 一帧。
//  如你的模块固件版本不同，请对照官方协议文档核对字段顺序。
// =============================================================
#pragma once
#include <Arduino.h>

#define LD2451_MAX_TARGETS 5

struct RadarTarget {
  int8_t  angle_deg;     // 负左正右
  uint8_t dist_m;
  bool    approaching;
  uint8_t speed_kmh;
  uint8_t snr;
};

struct RadarFrame {
  uint8_t     count;
  bool        alarm;
  RadarTarget targets[LD2451_MAX_TARGETS];
};

class LD2451 {
public:
  void begin(HardwareSerial *s) { ser = s; idx = 0; }

  // 有完整帧返回 true
  bool poll(RadarFrame &out) {
    while (ser && ser->available()) {
      uint8_t c = ser->read();
      if (idx < 4) {                       // 帧头同步
        static const uint8_t H[4] = {0xF4, 0xF3, 0xF2, 0xF1};
        if (c == H[idx]) buf[idx++] = c;
        else idx = (c == 0xF4) ? 1 : 0;
        continue;
      }
      buf[idx++] = c;
      if (idx == 6) {                      // 读到长度
        len = buf[4] | (buf[5] << 8);
        if (len > 2 + 5 * LD2451_MAX_TARGETS) { idx = 0; continue; }
      }
      if (idx >= 6 && idx == 6 + len + 4) {
        idx = 0;
        const uint8_t *tail = &buf[6 + len];
        if (tail[0] != 0xF8 || tail[1] != 0xF7 || tail[2] != 0xF6 || tail[3] != 0xF5) continue;
        return parse(&buf[6], len, out);
      }
      if (idx >= sizeof(buf)) idx = 0;
    }
    return false;
  }

private:
  HardwareSerial *ser = nullptr;
  uint8_t buf[64];
  size_t  idx = 0;
  uint16_t len = 0;

  bool parse(const uint8_t *d, uint16_t n, RadarFrame &out) {
    out.count = 0; out.alarm = false;
    if (n < 2) return false;
    uint8_t num = d[0];
    out.alarm = d[1] == 0x01;
    if (num > LD2451_MAX_TARGETS) num = LD2451_MAX_TARGETS;
    for (uint8_t i = 0; i < num && 2 + 5 * (i + 1) <= n; i++) {
      const uint8_t *t = &d[2 + 5 * i];
      RadarTarget &r = out.targets[out.count++];
      r.angle_deg   = (int8_t)(t[0] - 0x80);
      r.dist_m      = t[1];
      r.approaching = t[2] == 0x01;
      r.speed_kmh   = t[3];
      r.snr         = t[4];
    }
    return true;
  }
};
