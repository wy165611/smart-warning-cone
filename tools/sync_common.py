"""
把 firmware/common/ 下的 config.h、protocol.h 同步到每个固件目录。
Arduino IDE 只编译草图目录内的文件，所以每个目录都放了一份副本。
修改参数时只改 firmware/common/ 里的文件，然后运行：
    python tools/sync_common.py
"""
import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parent.parent / "firmware"
for sketch in ["sentinel", "follower", "worker", "gateway"]:
    for name in ["config.h", "protocol.h"]:
        shutil.copy2(root / "common" / name, root / sketch / name)
        print(f"common/{name} -> {sketch}/{name}")
