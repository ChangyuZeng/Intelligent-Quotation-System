"""启动/停止 uvicorn 子进程（单进程同时提供 API 与前端页面）。"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import paths, runtime_check

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


class ServerProcess:
    def __init__(self, port: int) -> None:
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.log_path = paths.logs_dir() / f"server-{datetime.now():%Y%m%d}.log"
        self._log_fp = None

    def build_env(self) -> dict[str, str]:
        env = runtime_check.clean_env()
        env.update(
            {
                # 三条绝对路径，彻底摆脱"工作目录不同读到不同数据"的历史问题
                "QUOTE_DATA_DIR": str(paths.data_dir()),
                "QUOTE_STATIC_DIR": str(paths.static_dir()),
                "HISTORY_SEED_PATH": str(paths.seed_file()),
                # 单端口同源，不再需要跨域
                "CORS_ORIGINS": "",
                "QUOTE_PORT": str(self.port),
            }
        )
        return env

    def start(self) -> subprocess.Popen:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_fp = open(self.log_path, "a", encoding="utf-8", errors="replace")
        self._log_fp.write(f"\n{'=' * 60}\n启动于 {datetime.now():%Y-%m-%d %H:%M:%S}  端口 {self.port}\n")
        self._log_fp.flush()

        self.proc = subprocess.Popen(
            [
                str(paths.python_exe()),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--log-level",
                "info",
            ],
            cwd=str(paths.server_dir()),  # 必须：否则 import app.main 失败
            env=self.build_env(),
            stdin=subprocess.DEVNULL,
            stdout=self._log_fp,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )
        return self.proc

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def exit_code(self) -> int | None:
        return None if self.proc is None else self.proc.poll()

    def log_tail(self, lines: int = 20) -> list[str]:
        try:
            content = self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        rows = [row for row in content.splitlines() if row.strip()]
        return rows[-lines:]

    def stop(self, timeout: float = 10.0) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            except OSError:
                pass
        if self._log_fp is not None:
            try:
                self._log_fp.close()
            except OSError:
                pass
            self._log_fp = None


def wait_until_ready(proc: subprocess.Popen, port: int, timeout: float = 90.0) -> tuple[bool, float]:
    """轮询 /api/health，直到服务可用或进程提前退出。"""
    import urllib.error
    import urllib.request

    # 同 ports.py：本机回环请求不能走系统代理
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    started = time.monotonic()
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() - started < timeout:
        if proc.poll() is not None:
            return False, time.monotonic() - started
        try:
            with opener.open(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True, time.monotonic() - started
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.25)
    return False, time.monotonic() - started


def ensure_writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def port_owner_hint(port: int) -> str:
    return f"端口 {port} 被其他程序占用"


def _unused() -> None:  # pragma: no cover - 保留给将来扩展
    os.getpid()
