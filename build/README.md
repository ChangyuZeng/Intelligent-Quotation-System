# 便携版构建说明

把本仓库构建成可以直接发给客户的文件夹。共三步，全部在仓库根目录执行。

最终产物结构：

```
智能报价系统_便携版/
├── 智能报价系统.exe     ← PyInstaller 打包，内嵌 启动图标.ico
├── 启动图标.ico
├── 安装与使用指引.md
├── runtime/             ← 便携 Python + 依赖（约 70MB）
├── runtime.zip          ← 运行时自修复备份（约 24MB）
├── server/              ← app + seed + static
├── data/                ← 客户数据（构建时从上一版拷入或留空）
└── logs/                ← 首次运行自动创建
```

---

## 第 1 步：构建前端 → `server/static`

```bash
cd frontend
npm install
npm run build      # vite.config.ts 里 outDir 已指向 ../server/static
```

产出 `server/static/{index.html, favicon.svg, assets/index-*.js|css}`。
这一步只是把界面编译成静态文件，**产物已入库**，只改后端时无需重复执行。

## 第 2 步：制作便携运行时 → `runtime/`

从任一**完整 CPython 3.13（Windows x64）** 安装目录复制，排除以下内容：

```
include/  libs/  Scripts/  Lib\site-packages/  Lib\ensurepip/
Lib\idlelib/  Lib\pydoc_data/  Lib\test/  Lib\tkinter/  *.pdb  __pycache__/
```

必须保留：`python.exe`、`python3.dll`、`python313.dll`、`vcruntime140.dll`、`vcruntime140_1.dll`、
`DLLs/`（含 `_sqlite3.pyd`、`sqlite3.dll`、`_ssl.pyd`、`_socket.pyd`、`_hashlib.pyd`）、`Lib/` 标准库。

然后安装依赖到运行时自己的 site-packages：

```powershell
& "$RUNTIME\python.exe" -m pip install --no-cache-dir --only-binary=:all: `
  --target "$RUNTIME\Lib\site-packages" -r build\requirements-portable.txt
```

写完整性标记 `runtime/RUNTIME_OK.txt`（启动器据此判断是否需要修复）：

```
format=1
python=3.13.14
built=2026-10-27
files=<runtime 下文件总数>
deps=fastapi,uvicorn,sqlalchemy,pydantic,openpyxl,xlrd,multipart
```

最后把整个 `runtime/` 压成 `runtime.zip`（压缩包内保留 `runtime/` 这一层前缀），作为自修复备份：

```powershell
Compress-Archive -Path runtime -DestinationPath runtime.zip -CompressionLevel Optimal
```

### 为什么移除 psycopg、为什么 uvicorn 不带 [standard]

- `psycopg` 在代码里零引用，本版只用 SQLite
- `uvicorn[standard]` 会引入 `uvloop`（Windows 无 wheel）、`watchfiles`（Rust 编译）、`httptools`，
  纯 Python 的 `uvicorn + h11` 完全够用，且避免任何编译依赖

### 验证运行时自包含

```cmd
runtime\python.exe -I -c "import sys,fastapi,uvicorn,sqlalchemy,openpyxl,xlrd,multipart,pydantic,sqlite3;print(sys.prefix)"
```

`sys.prefix` 必须指向包内 `runtime`，且无 ImportError。

## 第 3 步：打包启动器 → `智能报价系统.exe`

```powershell
python -m venv .venv
.\.venv\Scripts\pip install pyinstaller

.\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --console ^
  --name "智能报价系统" ^
  --icon "D:\绝对路径\启动图标.ico" ^
  --distpath "D:\输出目录" ^
  --workpath "build\pyi\work" --specpath "build\pyi" ^
  build\launcher_entry.py
```

> `--icon` 必须传**绝对路径**。PyInstaller 会把相对路径按 `--specpath` 解析，容易报
> `Icon input file ... not found`。

产物约 8.5MB（只含启动器逻辑与 Python 标准库，不含业务代码）。

---

## 自检与验收

启动器支持两个只用于自动化的环境变量：

| 变量 | 作用 |
| --- | --- |
| `QUOTE_LAUNCHER_SELFTEST=1` | 跑完启动流程即退出，不开浏览器、不等按键 |
| `QUOTE_LAUNCHER_HOLD=秒数` | 配合上一项，就绪后保持运行 N 秒，便于外部检查进程与端口 |

```cmd
set QUOTE_LAUNCHER_SELFTEST=1
智能报价系统.exe
```

建议至少覆盖：

1. 正常启动（就绪 ≤ 5 秒）
2. 删除 `runtime/` 后启动 → 应自动还原并正常启动
3. 占用 8000 端口后启动 → 应顺延到 8001 并在窗口显示实际端口
4. 重复双击 → 应识别"系统已在运行"并直接开浏览器
5. 关闭窗口 → `tasklist | findstr python` 应无残留
6. 路径含中文与空格、PATH 中无 Python/Node → 均应正常启动

## 常见坑

- **PyInstaller 找不到图标**：`--icon` 用绝对路径
- **`import app.main` 失败**：启动器已设置 `cwd=server`，手动起服务时也必须先 `cd server`
- **数据写到包外**：`server/app/database.py` 的 `_PROJECT_ROOT` 必须是 `parents[2]`（`server/app/x.py` → 包根）；
  启动器还会注入 `QUOTE_DATA_DIR` 绝对路径兜底
- **前端 404 或空白**：确认 `server/static/index.html` 存在；启动器日志会打印 `QUOTE_STATIC_DIR`
- **杀软误报**：PyInstaller onefile 常见，需在客户侧加白或做代码签名
