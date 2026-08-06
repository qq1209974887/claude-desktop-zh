# Claude Desktop 汉化补丁程序

> 本文档面向开发者，介绍项目技术细节与构建方法。
> **用户使用说明请查看 [DESCRIPTION.md](DESCRIPTION.md)。**

---

`Claude Desktop` 的 Web 层（聊天界面主体）硬编码了支持语言列表，其中不包含 `zh-CN`。因此即使存在 `zh-CN.json`，应用也会回退到 `en-US`。

## 一、汉化原理

本汉化补丁程序采用 **"让 `en-US` 槽位装载中文"** 的方案：不修改应用代码，而是将三个 `en-US.json` 文件的内容替换为对应的中文翻译。

## 二、汉化补丁程序操作指南

### 1、命令行参数支持

```bash 示例
# 无参数（默认） | 将中文翻译覆写到 `en-US.json` 槽位
python install.py --apply

# 从 `.bak` 备份恢复原始英文文件
python install.py --restore

# 手动指定 resources 目录
python install.py --path /path/to/resources

# 查看帮助信息
python install.py --help
python install.py --h
```

### 2、核心能力

- **跨平台自动探测** — 自动识别 Windows、macOS、Linux 下 Claude Desktop 的安装路径
- **交互式引导** — 使用 Vite 风格的方向键选择界面 (`questionary`)，降低使用门槛
- **自动安装 Python** — Bash 脚本在检测到无 Python 环境时会引导用户自动安装
- **自动备份** — 覆写前自动创建 `.bak` 备份，支持一键恢复
- **JSON 校验** — 覆写前验证源文件是否为合法 JSON，避免写入损坏数据
- **幂等备份** — 备份已存在时自动跳过，不会重复覆盖
- **错误隔离** — 单个文件操作失败不影响其他文件，最终汇总报告

## 三、文件对应关系

| 项目内源文件 | 应用内目标文件 | 作用 |
|-------------|---------------|------|
| `resources/zh-CN.json` | `resources/en-US.json` | Electron 原生层（菜单、对话框、托盘） |
| `resources/ion-dist/i18n/zh-CN.json` | `resources/ion-dist/i18n/en-US.json` | Web 界面主体（聊天、设置、项目） |
| `resources/ion-dist/i18n/dynamic/zh-CN.json` | `resources/ion-dist/i18n/dynamic/en-US.json` | 动态 UI 控件（模型选择器、思考模式） |

### 自动探测的安装路径

| 平台 | 路径 |
|------|------|
| **Windows** | `%LOCALAPPDATA%\AnthropicClaude\app-{version}\resources` |
| **macOS** | `/Applications/Claude.app/Contents/Resources` |
| **Linux** | `/usr/lib/claude-desktop/resources`、`/opt/claude-desktop/resources` 等 |

## 四、编译构建

### 快速构建（推荐）

```bash
# 自动尝试为所有平台构建，环境不匹配的将自动跳过
python scripts/build_exes.py
```

脚本会依次检测 Windows、macOS、Linux 三个平台的构建环境，对匹配的平台执行编译，不匹配的则跳过并在最后输出汇总报告。

### 各平台单独编译

> **注意**：PyInstaller 不支持跨平台编译，必须在目标平台上执行编译命令。

#### Windows 平台

```bash
# 方式一：使用 Python 构建脚本
python scripts/build_exes.py windows

# 方式二：直接使用 PyInstaller
python -m PyInstaller --clean --onefile --name claude-zh-patch ^
    --workpath scripts\build_temp --distpath dist --console ^
    --add-data "resources;resources" ^
    --hidden-import json --hidden-import questionary ^
    src\install.py
```

#### macOS 平台

```bash
# 方式一：使用 Python 构建脚本
python scripts/build_exes.py macos

# 方式二：直接使用 PyInstaller
python3 -m PyInstaller --clean --onefile --name claude-zh-patch \
    --workpath scripts/build_temp --distpath dist --console \
    --add-data "resources:resources" \
    --hidden-import json --hidden-import questionary \
    src/install.py
```

#### Linux 平台

```bash
# 方式一：使用 Python 构建脚本
python scripts/build_exes.py linux

# 方式二：使用 Bash 构建脚本
chmod +x scripts/build.sh
./scripts/build.sh

# 方式三：直接使用 PyInstaller
python3 -m PyInstaller --clean --onefile --name claude-zh-patch \
    --workpath scripts/build_temp --distpath dist --console \
    --add-data "resources:resources" \
    --hidden-import json --hidden-import questionary \
    src/install.py
```

### 构建产物

编译完成后 `dist/` 目录包含：

```
dist/
├── claude-zh-patch.exe          # Windows 单文件可执行程序
├── 使用说明.md                   # 用户使用说明
├── resources/                    # 翻译文件（嵌入至 exe 内部，同时附带用于命令行脚本）
├── src/                          # 命令行安装脚本
│   ├── install.py               # Python 主脚本
│   └── install.sh               # Bash 备用脚本（macOS / Linux）
└── build.log                     # 构建日志文件
```

构建完成后会自动清理中间产物（`scripts/build_temp/`、`*.spec` 文件）。

### GitHub Actions 自动构建

项目已配置 GitHub Actions，可自动在服务器上构建三个平台的可执行文件。

#### 工作流说明

| 工作流 | 触发条件 | 说明 |
|--------|----------|------|
| `build.yml` | 打标签 / 手动触发 | 构建三个平台的可执行文件 |
| `release.yml` | build.yml 成功后自动触发 | 创建 GitHub Release 并附加构建产物 |

#### 使用方式

**方式一：手动触发**
1. 进入 GitHub 仓库页面
2. 点击 **Actions** 标签
3. 选择 **Build** 工作流
4. 点击 **Run workflow**

**方式二：打标签发布**
```bash
git tag v1.0.0
git push origin v1.0.0
```

#### 构建产物

构建完成后，会在 GitHub Releases 页面生成：

| 平台 | 产物 | 说明 |
|------|------|------|
| Windows | `claude-zh-patch.exe` | 双击即可运行 |
| Linux | `claude-zh-patch` | 需要添加执行权限后运行 |
| macOS | `claude-zh-patch` | 需要添加执行权限后运行 |
| 通用 | `build-linux.log` | Linux 平台构建日志 |

每个产物都包含完整的 `resources/` 和 `src/` 目录。

> **提示**：构建日志 (`build.log`) 会同时保存在 `dist/` 目录和 GitHub Release 中，用于排查构建问题。

## 项目结构

```
claude-destktop-zh/
├── src/                        # 安装脚本
│   ├── install.py              # 主安装脚本（Python，Vite 风格交互）
│   └── install.sh              # macOS / Linux Bash 备用安装脚本
├── scripts/                    # 脚本工具集
│   ├── build_exes.py           # 主编译脚本（支持全平台自动检测与单平台指定构建）
│   ├── build.sh                # macOS / Linux 编译脚本（备选）
│   └── verify_artifacts.py     # 构建产物验证脚本
├── .github/                    # GitHub 配置
│   └── workflows/
│       ├── build.yml           # GitHub Actions 构建工作流
│       └── release.yml          # GitHub Actions 发布工作流
├── resources/                  # 中文翻译文件
│   ├── zh-CN.json              # Electron 原生层中文
│   └── ion-dist/i18n/
│       ├── zh-CN.json          # Web 界面主体中文
│       └── dynamic/zh-CN.json  # 动态 UI 控件中文
├── pyproject.toml              # PEP 621 项目配置
├── DESCRIPTION.md              # 用户使用说明
└── README.md                   # 开发者文档（本文件）
```

## 开发指南

### 环境要求

- Python >= 3.7
- `questionary` (>= 2.0)：交互式选择界面
- `PyInstaller` (>= 5.0)：打包为独立可执行文件

### 安装依赖

```bash
pip install -e .
# 或
pip install questionary pyinstaller
```
