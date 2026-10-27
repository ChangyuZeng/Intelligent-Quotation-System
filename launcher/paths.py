"""路径解析：所有路径都从 exe 所在目录派生，永不依赖当前工作目录（CWD）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def base_dir() -> Path:
    """包根目录。

    - 打包成 exe 后：exe 自身所在目录（用户可能从桌面快捷方式启动，CWD 是任意位置）
    - 源码调试时：可用 QUOTE_BASE_DIR 指定，否则按 _build/launcher/ 往上两级推断
    """
    override = os.environ.get("QUOTE_BASE_DIR")
    if override:
        return Path(override).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def runtime_dir() -> Path:
    return base_dir() / "runtime"


def python_exe() -> Path:
    return runtime_dir() / "python.exe"


def runtime_zip() -> Path:
    return base_dir() / "runtime.zip"


def runtime_marker() -> Path:
    return runtime_dir() / "RUNTIME_OK.txt"


def server_dir() -> Path:
    return base_dir() / "server"


def static_dir() -> Path:
    return server_dir() / "static"


def seed_file() -> Path:
    return server_dir() / "seed" / "history.json"


def data_dir() -> Path:
    return base_dir() / "data"


def logs_dir() -> Path:
    return base_dir() / "logs"
