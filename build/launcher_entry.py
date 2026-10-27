"""PyInstaller 打包入口。

构建命令（在仓库根目录执行）：

    python -m PyInstaller --noconfirm --clean --onefile --console ^
        --name "智能报价系统" --icon <ico 绝对路径> ^
        --distpath <输出目录> --workpath build/pyi/work --specpath build/pyi ^
        build/launcher_entry.py

注意：--icon 必须传**绝对路径**，否则 PyInstaller 会相对 --specpath 解析而找不到文件。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 源码运行时把仓库根目录加入 sys.path，使 `import launcher` 可用；
# 打包成 exe 后 launcher 已作为模块冻结，无需该路径。
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from launcher.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
