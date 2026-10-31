// =============================================================
//  ASRPRO 语音程序（天问 Block · 代码模式）
//  识别命令词 → 串口发送 AA 55 CMD SUM 给哨兵 ESP32-C3
//  接收哨兵回复 AA 55 81/82 SUM → 播报电量状态
//  说明：天问 Block 会根据 setup() 中 //{ID:...} 注释生成命令词模型，
//       注释格式不要改动；ID 与 ASR_CODE() 中 case 对应。
//  具体 API 名称以你安装的天问 Block 版本自动生成的模板为准。
// =============================================================
#include "asr.h"
extern "C"{ void * __dso_handle = 0 ;}
#include "setup.h"
#include "HardwareSerial.h"

uint32_t snid;
uint8_t  rxbuf[4];
uint8_t  rxidx = 0;

void send_cmd(uint8_t cmd){
  uint8_t sum = (uint8_t)(0xAA + 0x55 + cmd);
  Serial.write(0xAA);
  Serial.write(0x55);
  Serial.write(cmd);
  Serial.write(sum);
}

void ASR_CODE(){
  switch (snid) {
    case 1:  send_cmd(0x01); break;   // 开始作业
    case 2:  send_cmd(0x02); break;   // 结束作业
    case 3:  send_cmd(0x03); break;   // 左侧封道
    case 4:  send_cmd(0x04); break;   // 右侧封道
    case 5:  send_cmd(0x05); break;   // 雨天模式
    case 6:  send_cmd(0x06); break;   // 关闭雨天模式
    case 7:  send_cmd(0x07); break;   // 夜间模式
    case 8:  send_cmd(0x08); break;   // 关闭夜间模式
    case 9:  send_cmd(0x09); break;   // 报告电量（等回复再播报）
    case 10: send_cmd(0x0A); break;   // 设备自检
    default: break;
  }
}

// 串口接收任务：解析哨兵回复并播报
void uart_task(){
  while (1) {
    while (Serial.available() > 0) {
      uint8_t c = Serial.read();
      if (rxidx == 0 && c != 0xAA) continue;
      if (rxidx == 1 && c != 0x55) { rxidx = 0; continue; }
      rxbuf[rxidx++] = c;
      if (rxidx == 4) {
        rxidx = 0;
        if ((uint8_t)(rxbuf[0] + rxbuf[1] + rxbuf[2]) == rxbuf[3]) {
          if (rxbuf[2] == 0x81) play_audio(11);   // 播报“电量正常”
          if (rxbuf[2] == 0x82) play_audio(12);   // 播报“电量不足”
        }
      }
    }
    delay(10);
  }
  vTaskDelete(NULL);
}

void hardware_init(){
  Serial.begin(9600);
  xTaskCreate(uart_task, "uart_task", 256, NULL, 4, NULL);
  vTaskDelete(NULL);
}

void setup()
{
  //{ID:0,keyword:"唤醒词",ASR:"小哨兵",ASRTO:"我在"}
  //{ID:1,keyword:"命令词",ASR:"开始作业",ASRTO:"已开始作业，预警开启"}
  //{ID:2,keyword:"命令词",ASR:"结束作业",ASRTO:"已结束作业"}
  //{ID:3,keyword:"命令词",ASR:"左侧封道",ASRTO:"已切换左侧封道"}
  //{ID:4,keyword:"命令词",ASR:"右侧封道",ASRTO:"已切换右侧封道"}
  //{ID:5,keyword:"命令词",ASR:"雨天模式",ASRTO:"雨天模式已开启，预警距离加大"}
  //{ID:6,keyword:"命令词",ASR:"关闭雨天模式",ASRTO:"雨天模式已关闭"}
  //{ID:7,keyword:"命令词",ASR:"夜间模式",ASRTO:"夜间模式已开启"}
  //{ID:8,keyword:"命令词",ASR:"关闭夜间模式",ASRTO:"夜间模式已关闭"}
  //{ID:9,keyword:"命令词",ASR:"报告电量",ASRTO:"正在查询"}
  //{ID:10,keyword:"命令词",ASR:"设备自检",ASRTO:"开始自检"}
  //{ID:11,keyword:"命令词",ASR:"电量正常",ASRTO:"电量正常"}
  //{ID:12,keyword:"命令词",ASR:"电量不足",ASRTO:"电量不足，请及时充电"}
}
