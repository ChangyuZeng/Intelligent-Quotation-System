"""控制台输出：同时写屏幕与 logs/launcher-YYYYMMDD.log，便于售后排错。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# 中文提示很多；控制台是真实终端时 Python 走 WriteConsoleW 不会乱码，
# 只有在被重定向到文件时才需要容错，避免个别字符抛 UnicodeEncodeError。
try:
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


class Console:
    def __init__(self, log_path: Path | None = None) -> None:
        self._fp = None
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                self._fp = open(log_path, "a", encoding="utf-8", errors="replace")
                self._fp.write("\n" + "=" * 60 + "\n")
                self._fp.write(f"启动于 {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            except OSError:
                self._fp = None

    def write(self, text: str = "", *, end: str = "\n") -> None:
        sys.stdout.write(text + end)
        sys.stdout.flush()
        if self._fp is not None:
            try:
                self._fp.write(text + end)
                self._fp.flush()
            except OSError:
                pass

    def step(self, index: int, total: int, title: str, detail: str = "") -> None:
        head = f"[{index}/{total}] {title}"
        self.write(f"{head} ... {detail}" if detail else f"{head} ...")

    def ok(self, text: str) -> None:
        self.write(f"      通过  {text}" if text else "      通过")

    def warn(self, text: str) -> None:
        self.write(f"      注意  {text}")

    def fail(self, text: str) -> None:
        self.write(f"      失败  {text}")

    def close(self) -> None:
        if self._fp is not None:
            try:
                self._fp.close()
            except OSError:
                pass
            self._fp = None
