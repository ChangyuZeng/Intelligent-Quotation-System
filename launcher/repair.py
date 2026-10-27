"""运行时自修复：runtime.zip → runtime（解压到临时目录再原子替换）。"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from . import paths


class RepairError(RuntimeError):
    pass


def _safe_extract(zip_path: Path, target: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            name = member.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                raise RepairError("备份包内容异常，已中止解压")
        archive.extractall(target)


def extract_runtime(on_progress=None) -> None:
    """把 runtime.zip 解压并替换 runtime/。失败时保留旧目录，绝不半途覆盖。"""
    archive = paths.runtime_zip()
    if not archive.is_file():
        raise RepairError("缺少运行环境备份文件 runtime.zip")

    runtime = paths.runtime_dir()
    temp = runtime.with_name("runtime.tmp")
    old = runtime.with_name("runtime.old")

    for leftover in (temp, old):
        if leftover.exists():
            shutil.rmtree(leftover, ignore_errors=True)

    if on_progress:
        on_progress("正在解压运行环境备份…")
    try:
        _safe_extract(archive, temp)
    except (zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(temp, ignore_errors=True)
        raise RepairError(f"运行环境备份已损坏（{exc}）") from exc

    # 备份包内是 runtime/ 结构还是平铺结构，两种都兼容
    source = temp / "runtime" if (temp / "runtime" / "python.exe").is_file() else temp
    if not (source / "python.exe").is_file():
        shutil.rmtree(temp, ignore_errors=True)
        raise RepairError("运行环境备份内容不完整")

    if runtime.exists():
        runtime.rename(old)
    try:
        source.rename(runtime)
    except OSError as exc:
        if old.exists() and not runtime.exists():
            old.rename(runtime)
        shutil.rmtree(temp, ignore_errors=True)
        raise RepairError(f"无法写入运行环境目录：{exc}") from exc

    shutil.rmtree(temp, ignore_errors=True)
    shutil.rmtree(old, ignore_errors=True)
    if on_progress:
        on_progress("运行环境已恢复")
