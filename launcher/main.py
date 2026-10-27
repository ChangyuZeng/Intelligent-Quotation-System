"""启动器编排：检测环境 → (必要时)自修复 → 起服务 → 开浏览器 → 状态窗口。"""

from __future__ import annotations

import os
import sys
import time
import webbrowser
from datetime import datetime

from . import paths, ports, repair, runtime_check, server_proc, winjob
from .console import Console

TOTAL = 5
WINDOW_TITLE = "智能报价系统"
BANNER = (
    "============================================================\n"
    "  智能报价系统 · 便携版\n"
    "  单机运行，无需安装任何软件\n"
    "============================================================"
)


def _set_title() -> None:
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(WINDOW_TITLE)
    except Exception:
        pass


def _pause(console: Console, message: str = "按任意键关闭窗口…") -> None:
    if _headless():
        return
    console.write("")
    console.write(message, end="")
    try:
        import msvcrt

        msvcrt.getwch()
    except Exception:
        time.sleep(8)
    console.write("")


def _headless() -> bool:
    """自动化验收用：跑完启动流程即退出，不等待按键、不打开浏览器。"""
    return os.environ.get("QUOTE_LAUNCHER_SELFTEST") == "1"


def _open(url: str) -> None:
    if _headless():
        return
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def _status_line(console: Console, text: str) -> None:
    """原地刷新一行，不写入日志文件。"""
    try:
        sys.stdout.write("\r" + text + " " * 12)
        sys.stdout.flush()
    except Exception:
        pass


def _fail(console: Console, title: str, hint: str) -> int:
    console.write("")
    console.write(f"  ✗ {title}")
    console.write(f"    {hint}")
    console.write("")
    console.write(f"    日志目录：{paths.logs_dir()}")
    _pause(console)
    return 1


def _check_runtime(console: Console) -> tuple[bool, str]:
    """检测内置运行环境，必要时从 runtime.zip 自动修复。"""
    ready, detail = runtime_check.is_ready()
    if ready:
        passed, version = runtime_check.smoke_test()
        if passed:
            return True, version
        console.warn(f"运行环境自检未通过（{version}），开始自动修复")
    else:
        console.warn(f"{detail}，开始自动修复")

    if not paths.runtime_zip().is_file():
        console.fail("无法自动修复：缺少 runtime.zip")
        return False, "缺少运行环境备份"

    console.write("      正在修复运行环境（约 20 秒），请勿关闭窗口…")
    try:
        repair.extract_runtime(on_progress=lambda msg: console.write(f"      {msg}"))
    except repair.RepairError as exc:
        console.fail(str(exc))
        return False, str(exc)

    passed, version = runtime_check.smoke_test()
    if passed:
        console.ok(f"已自动修复（Python {version}）")
        return True, version
    console.fail(f"修复后仍不可用：{version}")
    return False, version


def _run(console: Console) -> int:
    console.write(BANNER)
    console.write("")

    # ---- 1/5 目录与写权限 ----
    console.step(1, TOTAL, "检查文件夹")
    if not server_proc.ensure_writable(paths.logs_dir()):
        console.fail(f"无法写入 {paths.logs_dir()}")
        return _fail(
            console,
            "当前文件夹不可写入",
            "请把整个文件夹复制到桌面或 D 盘，再双击「智能报价系统.exe」",
        )
    if not paths.server_dir().is_dir() or not (paths.server_dir() / "app" / "main.py").is_file():
        return _fail(console, "程序文件缺失", "server 文件夹不完整，请重新解压整个文件夹")
    console.ok(str(paths.base_dir()))

    # ---- 2/5 运行环境 ----
    console.step(2, TOTAL, "检查运行环境")
    ok, version = _check_runtime(console)
    if not ok:
        return _fail(
            console,
            "运行环境损坏且无法自动修复",
            "请把整个压缩包重新解压一次（务必解压全部文件，不要只解压一部分）",
        )
    console.ok(f"内置 Python {version}")

    # ---- 3/5 数据目录 ----
    console.step(3, TOTAL, "检查数据目录")
    if not server_proc.ensure_writable(paths.data_dir()):
        return _fail(console, "数据目录不可写", "请把整个文件夹复制到桌面或 D 盘后再试")
    db_file = paths.data_dir() / "quote_saitel.db"
    if db_file.is_file():
        console.ok(f"{db_file.name}（{db_file.stat().st_size / 1024 / 1024:.1f} MB）")
    else:
        console.warn("未找到既有数据库，将新建空库并导入历史价种子")

    if not paths.static_dir().is_dir():
        console.warn("未找到界面文件 server/static，系统只能提供接口")

    # ---- 4/5 端口 ----
    console.step(4, TOTAL, "准备服务端口")
    existing = ports.running_instance()
    if existing is not None:
        url = f"http://127.0.0.1:{existing}"
        console.ok(f"系统已在运行，端口 {existing}")
        console.write("")
        console.write(f"  已在浏览器中打开：{url}")
        console.write("  如果浏览器没有反应，请手动复制上面的地址到浏览器打开。")
        _open(url)
        _pause(console)
        return 0

    port = ports.pick()
    if port is None:
        return _fail(
            console,
            "端口 8000-8010 全部被占用",
            "请关闭其他正在运行的程序（尤其是重复打开的报价系统），再重新双击",
        )
    console.ok(f"使用端口 {port}")

    # ---- 5/5 启动服务 ----
    console.step(5, TOTAL, "启动服务")
    server = server_proc.ServerProcess(port)
    job = None
    try:
        proc = server.start()
    except OSError as exc:
        return _fail(console, "无法启动服务进程", f"{exc}")

    try:
        job = winjob.Job()
        job.attach(proc.pid)
    except Exception:
        job = None  # 拿不到 Job 也不影响使用，只是关窗后可能残留进程

    try:
        console.write(f"      正在加载数据，请稍候…（日志：{server.log_path.name}）")
        ready, elapsed = server_proc.wait_until_ready(proc, port)
        if not ready:
            console.write("")
            console.fail("服务未能启动")
            for row in server.log_tail(15):
                console.write(f"      {row}")
            return _fail(
                console,
                "启动失败",
                "请把 logs 文件夹里最新的日志文件发给技术支持",
            )

        url = f"http://127.0.0.1:{port}"
        console.ok(f"已就绪，用时 {elapsed:.1f} 秒")

        console.write("")
        console.write("=" * 60)
        console.write(f"  访问地址： {url}")
        console.write(f"  数据目录： {paths.data_dir()}")
        console.write(f"  运行日志： {server.log_path}")
        console.write("")
        console.write("  按 O 重新打开浏览器    按 Q 退出")
        console.write("  直接关闭本窗口即可停止系统")
        console.write("=" * 60)
        console.write("")

        _open(url)
        if _headless():
            # 验收用：保持运行若干秒，便于外部检查进程树与端口
            hold = os.environ.get("QUOTE_LAUNCHER_HOLD")
            if hold:
                try:
                    time.sleep(float(hold))
                except ValueError:
                    pass
            return 0
        return _loop(console, server, url)
    finally:
        server.stop()
        if job is not None:
            job.close()


def _loop(console: Console, server: server_proc.ServerProcess, url: str) -> int:
    started = time.monotonic()
    try:
        import msvcrt
    except Exception:
        msvcrt = None

    while True:
        if not server.alive():
            code = server.exit_code()
            _status_line(console, "")
            console.write("")
            console.fail(f"服务已退出（退出码 {code}）")
            for row in server.log_tail(15):
                console.write(f"      {row}")
            return _fail(console, "服务异常退出", "请把 logs 文件夹里最新的日志发给技术支持")

        if msvcrt is not None and msvcrt.kbhit():
            key = msvcrt.getwch().lower()
            if key == "q":
                console.write("")
                console.write("  正在退出…")
                return 0
            if key == "o":
                _open(url)
            if key == "\x03":  # Ctrl+C
                return 0

        span = int(time.monotonic() - started)
        clock = f"{span // 3600:02d}:{span % 3600 // 60:02d}:{span % 60:02d}"
        _status_line(console, f"  ● 运行中   已运行 {clock}   地址 {url}   （O 重开浏览器 / Q 退出）")
        time.sleep(1)


def main() -> int:
    _set_title()
    paths.logs_dir().mkdir(parents=True, exist_ok=True)
    console = Console(paths.logs_dir() / f"launcher-{datetime.now():%Y%m%d}.log")
    try:
        return _run(console)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # 兜底：任何未预期异常都要给用户可读信息
        console.write("")
        console.write(f"  ✗ 启动器异常：{exc!r}")
        console.write(f"    请把 {paths.logs_dir()} 里的日志发给技术支持")
        _pause(console)
        return 1
    finally:
        console.close()
