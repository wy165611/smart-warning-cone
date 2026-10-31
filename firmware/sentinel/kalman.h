// 一维卡尔曼滤波（常值模型），用于平滑雷达距离与速度
//   q：过程噪声，越大跟随越快；r：测量噪声，越大越平滑
#pragma once

class Kalman1D {
public:
  Kalman1D(float q, float r) : q(q), r(r) {}
  void reset() { init = false; }
  float update(float z) {
    if (!init) { x = z; p = r; init = true; return x; }
    p += q;                       // 预测
    float k = p / (p + r);        // 增益
    x += k * (z - x);             // 更新
    p *= (1 - k);
    return x;
  }
private:
  float q, r, x = 0, p = 1;
  bool init = false;
};
