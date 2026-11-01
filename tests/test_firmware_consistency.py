"""固件与 Python 参考实现之间的“对账”测试：改了一边忘了另一边时会失败。"""

import re
from pathlib import Path

from sentinel import algorithm, voice

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware"
SKETCHES = ("sentinel", "follower", "worker", "gateway")


def _defines(path: Path) -> dict[str, str]:
    pattern = re.compile(r"^\s*#define\s+(\w+)\s+(\S+)", re.MULTILINE)
    return dict(pattern.findall(path.read_text(encoding="utf-8")))


def _number(raw: str) -> float:
    return float(raw.rstrip("fF"))


def test_sketch_headers_are_identical_to_common() -> None:
    for sketch in SKETCHES:
        for name in ("config.h", "protocol.h"):
            common = (FIRMWARE / "common" / name).read_bytes()
            copy = (FIRMWARE / sketch / name).read_bytes()
            assert copy == common, f"{sketch}/{name} 与 common 不一致，运行 tools/sync_common.py"


def test_thresholds_match_config_h() -> None:
    cfg = _defines(FIRMWARE / "common" / "config.h")
    pairs = {
        "TTC_LEVEL1_S": algorithm.TTC_LEVEL1_S,
        "TTC_LEVEL2_S": algorithm.TTC_LEVEL2_S,
        "SPEED_LIMIT_KMH": algorithm.SPEED_LIMIT_KMH,
        "OVERSPEED_RATIO": algorithm.OVERSPEED_RATIO,
        "RAIN_FACTOR": algorithm.RAIN_FACTOR,
        "NIGHT_FACTOR": algorithm.NIGHT_FACTOR,
        "CONFIRM_FRAMES": algorithm.CONFIRM_FRAMES,
        "MIN_TRACK_SPEED": algorithm.MIN_TRACK_SPEED_KMH,
        "MAX_TRACK_DIST": algorithm.MAX_TRACK_DIST_M,
    }
    for name, value in pairs.items():
        assert _number(cfg[name]) == value, name


def test_kalman_parameters_match_sentinel_sketch() -> None:
    text = (FIRMWARE / "sentinel" / "sentinel.ino").read_text(encoding="utf-8")
    found = re.findall(r"kf\w+\(([\d.]+)f,\s*([\d.]+)f\)", text)
    assert found, "没有找到 Kalman1D 构造参数"
    reference = algorithm.Kalman1D()
    for q, r in found:
        assert (float(q), float(r)) == (reference.q, reference.r)


def test_voice_command_codes_match_protocol_h() -> None:
    text = (FIRMWARE / "common" / "protocol.h").read_text(encoding="utf-8")
    codes = {
        name: int(value, 16) for name, value in re.findall(r"(VC_\w+)\s*=\s*(0x[0-9A-Fa-f]+)", text)
    }
    assert codes["VC_START_WORK"] == voice.CMD_START_WORK
    assert codes["VC_STOP_WORK"] == voice.CMD_STOP_WORK
    assert codes["VC_LEFT"] == voice.CMD_LEFT
    assert codes["VC_RIGHT"] == voice.CMD_RIGHT
    assert codes["VC_RAIN_ON"] == voice.CMD_RAIN_ON
    assert codes["VC_RAIN_OFF"] == voice.CMD_RAIN_OFF
    assert codes["VC_NIGHT_ON"] == voice.CMD_NIGHT_ON
    assert codes["VC_NIGHT_OFF"] == voice.CMD_NIGHT_OFF
    assert codes["VC_BATTERY"] == voice.CMD_BATTERY
    assert codes["VC_TEST"] == voice.CMD_TEST
    replies = _defines(FIRMWARE / "common" / "protocol.h")
    assert int(replies["VOICE_REPLY_BATT_OK"], 16) == voice.REPLY_BATT_OK
    assert int(replies["VOICE_REPLY_BATT_LOW"], 16) == voice.REPLY_BATT_LOW


def test_config_h_keeps_placeholder_credentials() -> None:
    cfg = _defines(FIRMWARE / "common" / "config.h")
    assert cfg["WIFI_SSID"] == '"YourWiFi"'
    assert cfg["WIFI_PASS"] == '"YourPassword"'
