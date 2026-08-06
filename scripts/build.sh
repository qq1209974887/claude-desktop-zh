#!/bin/bash
# Claude-Desktop 汉化程序 - macOS / Linux 编译脚本
# 用法：
#   chmod +x scripts/build.sh
#   ./scripts/build.sh

set -euo pipefail

# 脚本在 scripts/ 子目录，项目根目录是父目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/scripts/build_temp"
DIST_DIR="$PROJECT_DIR/dist"

echo "=================================================="
echo "Claude-Desktop 汉化程序 - macOS / Linux 编译脚本"
echo "=================================================="
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "[错误] 未找到 Python，请先安装 Python 3.7+" >&2
        echo "macOS: brew install python3" >&2
        echo "Linux: sudo apt install python3 (Debian/Ubuntu) / sudo dnf install python3 (Fedora)" >&2
        exit 1
    fi
else
    PYTHON_CMD="python3"
fi

echo "[OK] Python 已安装：$($PYTHON_CMD --version)"

# 检查 PyInstaller
if ! $PYTHON_CMD -m pip show pyinstaller &>/dev/null; then
    echo "[警告] PyInstaller 未安装，正在安装..."
    $PYTHON_CMD -m pip install pyinstaller
    echo "[OK] PyInstaller 安装成功"
else
    echo "[OK] PyInstaller 已安装"
fi

# 清理旧文件
if [[ -d "$BUILD_DIR" ]]; then
    rm -rf "$BUILD_DIR"
    echo "[清理] 已删除旧的 build_temp 目录"
fi
if [[ -d "$DIST_DIR" ]]; then
    rm -rf "$DIST_DIR"
    echo "[清理] 已删除旧的 dist 目录"
fi

echo ""
echo "开始编译可执行文件..." >&2

# 检测平台
case "$(uname -s)" in
    Darwin)
        PLATFORM_NAME="macOS"
        EXE_NAME="claude-zh-patch-macos"
        ;;
    Linux)
        PLATFORM_NAME="Linux"
        EXE_NAME="claude-zh-patch-linux"
        ;;
esac

# PyInstaller 编译
if $PYTHON_CMD -m PyInstaller \
    --clean --onefile --name "$EXE_NAME" \
    --distpath "$DIST_DIR" --workpath "$BUILD_DIR" \
    --add-data "$PROJECT_DIR/resources:resources" \
    --hidden-import json \
    --hidden-import questionary \
    "$PROJECT_DIR/src/install.py"; then

    EXE_PATH="$DIST_DIR/$EXE_NAME"
    if [[ -f "$EXE_PATH" ]]; then
        SIZE_MB=$(du -h "$EXE_PATH" | cut -f1)
        echo ""
        echo "=================================================="
        echo "[完成] $PLATFORM_NAME 可执行文件已生成"
        echo "位置：$EXE_PATH"
        echo "大小：$SIZE_MB"
        echo "=================================================="

        # 添加执行权限
        chmod +x "$EXE_PATH"
        echo "[OK] 已添加执行权限"
    fi
else
    echo ""
    echo "[错误] 编译失败" >&2
    exit 1
fi
