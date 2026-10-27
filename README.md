# 智能报价系统（Intelligent Quotation System）

基于历史采购价目库的实验教学仪器自动报价系统：上传采购清单 Excel，系统自动匹配历史价目、生成多制造商候选方案，复核后导出客户版 / 内部复核版报价单。

## 功能概览

- **报价任务**：上传询价单（.xlsx / .xlsm / .xls / .csv）→ 自动匹配历史价目 → 人工复核 → 一键导出
- **多厂商报价**：每个产品可输出最多 5 个不同制造商的候选方案（导出为 报价1~报价N 列组）
- **价目库管理**：多库并存，新建/重命名/删除/导入价目本，表格化编辑、质量治理、审计留痕
- **任务级绑定**：每个报价任务显式绑定所用价目库，互不干扰

## 交付形态（2026-10 起）

**Windows 便携版**：一个文件夹 + 一个 `智能报价系统.exe`，双击即用。

- 不需要目标电脑安装 Python、Node.js 或 VC++ 运行库
- 不需要联网；运行环境（约 70MB）随包分发
- 单进程、单端口（默认 `127.0.0.1:8000`），关闭窗口即停止
- 运行环境缺失或损坏时，启动器会从 `runtime.zip` 自动还原（约 20–30 秒）

面向最终用户的操作说明见 [安装与使用指引.md](安装与使用指引.md)。

## 架构

```
智能报价系统.exe            启动器（PyInstaller，内嵌图标）
  └─ runtime\python.exe     包内便携 Python 3.13 + 全部依赖
       └─ uvicorn app.main:app
            ├─ /api/*       FastAPI 后端
            └─ /*           server/static 前端静态文件（同一端口）
```

启动器负责：环境自检与自修复 → 端口选择（8000→8010 自动顺延）→ 起服务 → 探活 → 打开浏览器 →
状态窗口（关窗时通过 Job Object 杀掉子进程，不留残留）。

## 目录结构

```
├── 智能报价系统.exe          # 交付入口（构建产物，不入库）
├── runtime/                 # 便携 Python + 依赖（构建产物，不入库）
├── runtime.zip              # 运行时自修复备份（构建产物，不入库）
├── data/                    # 运行数据：价目库 .db、上传/导出件（不入库）
├── logs/                    # 运行日志（不入库）
├── launcher/                # 启动器源码
│   ├── main.py              # 编排：检测 → 修复 → 起服务 → 状态窗口
│   ├── paths.py             # 路径解析（永不依赖 CWD）
│   ├── runtime_check.py     # 标记文件 + import 冒烟测试
│   ├── repair.py            # 从 runtime.zip 原子还原
│   ├── ports.py             # 端口探测（强制绕过系统代理）
│   ├── server_proc.py       # 子进程生命周期与日志
│   ├── winjob.py            # Job Object：关窗即杀
│   └── console.py           # 控制台输出（同时写日志文件）
├── server/
│   ├── app/                 # FastAPI 后端（包名必须为 app）
│   ├── seed/history.json    # 历史价种子（空库首启导入）
│   ├── static/              # 前端构建产物（入库，clone 后可直接运行）
│   └── tests/               # pytest 用例
├── frontend/                # Vite + React 前端源码
├── build/                   # 打包入口、依赖清单、构建说明
├── docs/                    # 设计与交付文档
└── 测试数据/                 # pytest 夹具（真实询价单）
```

## 快速开始（开发）

```bash
# 1. 前端（改动界面时）
cd frontend && npm install && npm run build   # 产物输出到 server/static

# 2. 后端（需要一个 Python 3.11+ 环境）
cd server
pip install -r ../build/requirements-portable.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 打开 http://127.0.0.1:8000
```

默认账号：`admin` / `admin123`（管理员）、`quote` / `quote123`（报价员）。

## 构建便携版

见 [build/README.md](build/README.md)。三步：构建前端 → 复制并安装便携运行时 → PyInstaller 打包 exe。

## 测试

```bash
cd server && python -m pytest tests -q     # 当前基线：134 passed, 3 skipped
```

## 技术栈

- 前端：React 19 + Vite 8 + Tailwind CSS 4（构建为静态文件，运行时不需要 Node）
- 后端：FastAPI + Uvicorn + SQLAlchemy + SQLite（每库独立 `.db`）
- 启动器：纯标准库 Python + PyInstaller onefile + Win32 Job Object

## 2026-10 更新摘要

- **改为 Windows 便携版**：去掉 Node.js 运行时依赖，前端预编译为静态文件由后端同端口托管；内置便携 Python，用户零安装、离线可用
- **一键 exe**：`启动.bat` + `windows-setup.ps1` 的联网安装链路整体废弃，替换为内嵌图标的单文件 exe
- **环境自修复**：`runtime` 缺失或损坏时从 `runtime.zip` 自动还原，无需重装
- **代理兼容**：健康检查强制绕过系统 HTTP 代理，避免公司网络下误判启动失败
- **仓库重构**：`demo-app/` 拆分为 `server/`（后端 + 静态产物 + 测试）与 `frontend/`（Vite 源码），新增 `launcher/` 与 `build/`

历史版本变更见 `docs/` 与 git log。

## 数据安全

`data/`（价目库、客户、报价记录）已在 `.gitignore` 中排除，**不会进入本仓库**。
本仓库为公开仓库，请勿提交任何客户数据或价目数据。
