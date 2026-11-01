from pathlib import Path

from tools.sync_common import sync_common


def test_sync_copies_headers_and_errors_when_missing(tmp_path: Path) -> None:
    firmware = tmp_path / "firmware"
    common = firmware / "common"
    common.mkdir(parents=True)
    (common / "config.h").write_text("config", encoding="utf-8")
    (common / "protocol.h").write_text("protocol", encoding="utf-8")
    copied = sync_common(firmware)
    assert len(copied) == 8
    assert (firmware / "gateway" / "protocol.h").read_text(encoding="utf-8") == "protocol"
    (common / "config.h").unlink()
    try:
        sync_common(firmware)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")
