from sentinel.radar import FrameParser
from sentinel.voice import CMD_START_WORK, checksum, decode, encode

# 《LD2451 串口通信协议 V1.03》数据实例。示例正文把方向说反了，这里按表 9 解析。
OFFICIAL = bytes.fromhex("F4F3F2F1110003018A28003C158A1E013C0F765F003C0FF8F7F6F5")


def test_official_example_frame() -> None:
    frames = FrameParser().feed(b"\x00\x11" + OFFICIAL + b"\xff")
    assert len(frames) == 1
    frame = frames[0]
    assert frame.alarm is True
    assert [(t.angle_deg, t.dist_m, t.approaching, t.speed_kmh, t.snr) for t in frame.targets] == [
        (10, 40, False, 60, 21),
        (10, 30, True, 60, 15),
        (-10, 95, False, 60, 15),
    ]


def test_parser_survives_split_chunks_and_does_not_grow_on_noise() -> None:
    parser = FrameParser()
    assert parser.feed(OFFICIAL[:8]) == []
    frames = parser.feed(OFFICIAL[8:])
    assert len(frames) == 1
    parser.feed(b"\x00" * 5000)
    assert len(parser._buf) < 16


def test_rejects_overlong_length_and_resynchronizes() -> None:
    bad = b"\xf4\xf3\xf2\xf1\xff\x00" + OFFICIAL
    frames = FrameParser().feed(bad)
    assert len(frames) == 1


def test_voice_start_work_checksum_and_reject_bad_sum() -> None:
    frame = encode(CMD_START_WORK)
    assert frame == bytes.fromhex("AA550100")
    assert checksum(CMD_START_WORK) == 0x00
    assert decode(frame) == CMD_START_WORK
    assert decode(bytes.fromhex("AA550101")) is None
    assert decode(bytes.fromhex("AA560100")) is None
