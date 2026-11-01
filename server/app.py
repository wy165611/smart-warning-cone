"""兼容入口。在 server 目录执行 python app.py，或从仓库根目录 python -m sentinel。"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sentinel.__main__ import main  # noqa: E402
from sentinel.api import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    main(app)
