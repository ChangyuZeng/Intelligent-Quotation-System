"""运行环境检测：文件存在性 + 标记文件 + 真正 import 一次做冒烟测试。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import paths

# 只 import，不执行业务逻辑：能全部导入就说明依赖与 .pyd 都完整。
# 末尾两条断言保证依赖确实来自包内 runtime，而不是机器上另装的 Python。
SMOKE_CODE = (
    "import sys, os, sqlite3, ssl, hashlib\n"
    "import fastapi, uvicorn, sqlalchemy, openpyxl, xlrd, multipart, pydantic\n"
    "prefix = os.path.normcase(sys.prefix)\n"
    "assert os.path.normcase(fastapi.__file__).startswith(prefix), '依赖不在包内运行时'\n"
    "print(sys.version.split()[0])\n"
)

CREATE_NO_WINDOW = 0x08000000


def clean_env() -> dict[str, str]:
    """剔除会把 Python 指向别处的变量，保证只用包内运行时。"""
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONEXECUTABLE"):
        env.pop(key, None)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def read_marker() -> dict[str, str]:
    marker = paths.runtime_marker()
    info: dict[str, str] = {}
    if not marker.is_file():
        return info
    try:
        for line in marker.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                info[key.strip()] = value.strip()
    except OSError:
        return {}
    return info


def smoke_test(timeout: int = 90) -> tuple[bool, str]:
    """在隔离模式（-I）下真正启动一次运行时。返回 (是否通过, 版本或错误摘要)。"""
    python = paths.python_exe()
    if not python.is_file():
        return False, "缺少 runtime\\python.exe"
    try:
        result = subprocess.run(
            [str(python), "-I", "-c", SMOKE_CODE],
            capture_output=True,
            timeout=timeout,
            env=clean_env(),
            creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return False, "运行环境响应超时"
    except OSError as exc:
        return False, f"无法执行运行环境：{exc}"
    if result.returncode != 0:
        tail = (result.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        return False, tail[-1] if tail else f"退出码 {result.returncode}"
    version = (result.stdout or b"").decode("utf-8", "replace").strip()
    return True, version or "OK"


def is_ready() -> tuple[bool, str]:
    """快速判断（不跑冒烟），用于决定是否需要进入修复流程。"""
    if not paths.python_exe().is_file():
        return False, "缺少 runtime\\python.exe"
    marker = read_marker()
    if not marker:
        return False, "缺少运行时标记文件 RUNTIME_OK.txt"
    if marker.get("format") != "1":
        return False, "运行时标记版本不匹配"
    return True, marker.get("python", "未知版本")
