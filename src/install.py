#!/usr/bin/env python3
"""
Claude-Desktop 汉化安装程序
兼容 Windows / macOS / Linux

用法:
    python install.py              # 交互式安装（Vite 风格方向键选择）
    python install.py --apply      # 快捷模式：跳过交互，直接汉化
    python install.py --restore    # 快捷模式：跳过交互，直接恢复英文原版
    python install.py --path /Applications/Claude.app/Contents/Resources  # 指定路径
"""

import argparse
import json
import os
import shutil
import sys

from pathlib import Path
from typing import List, Optional, Tuple

# 修复 Windows 控制台编码问题，确保 Unicode 字符能正常输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 尝试导入 questionary（交互式选择库）
try:
    import questionary
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False


# 汉化文件映射: (项目内的源文件, 应用内要被覆写的目标文件)
PATCH_MAP: List[Tuple[str, str]] = [
    ("resources/zh-CN.json", "en-US.json"),
    ("resources/ion-dist/i18n/zh-CN.json", "ion-dist/i18n/en-US.json"),
    ("resources/ion-dist/i18n/dynamic/zh-CN.json", "ion-dist/i18n/dynamic/en-US.json"),
]

BANNER = r"""
  ╔══════════════════════════════════════════╗
  ║     Claude-Desktop 中文本地化补丁       ║
  ║                  v1.0.0                  ║
  ╚══════════════════════════════════════════╝
"""

BANNER_SUBTITLE = "汉化方式：让 en-US 翻译槽位装载中文资源"


def get_project_dir() -> Path:
    """获取汉化项目根目录（兼容脚本运行和 PyInstaller 打包）"""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    script_dir = Path(__file__).resolve().parent
    if (script_dir / "resources").is_dir():
        return script_dir
    if (script_dir.parent / "resources").is_dir():
        return script_dir.parent
    return script_dir.parent


def find_all_claude_resources() -> List[Path]:
    """自动探测所有 Claude-Desktop 的 resources 目录"""
    system = sys.platform
    candidates: List[Path] = []

    if system == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            local_appdata = str(Path.home() / "AppData/Local")
        base = Path(local_appdata) / "AnthropicClaude"
        if base.exists():
            app_dirs = sorted(
                [p for p in base.iterdir() if p.is_dir() and p.name.startswith("app-")],
                key=lambda p: p.name,
                reverse=True,
            )
            candidates.extend(d / "resources" for d in app_dirs)

    elif system == "darwin":
        candidates = [
            Path("/Applications/Claude.app/Contents/Resources"),
            Path.home() / "Applications/Claude.app/Contents/Resources",
        ]

    else:
        candidates = [
            Path("/usr/lib/claude-desktop/resources"),
            Path("/opt/claude-desktop/resources"),
            Path.home() / ".local/lib/claude-desktop/resources",
            Path("/usr/share/claude-desktop/resources"),
        ]
        linux_base = Path.home() / ".local/share/claude-desktop"
        if linux_base.exists():
            app_dirs = sorted(
                [p for p in linux_base.iterdir() if p.is_dir() and p.name.startswith("app-")],
                key=lambda p: p.name,
                reverse=True,
            )
            candidates.extend(d / "resources" for d in app_dirs)

    valid = [c for c in candidates if (c / "en-US.json").is_file()]
    return valid


def find_claude_resources() -> Optional[Path]:
    """自动探测 Claude-Desktop 的 resources 目录"""
    all_dirs = find_all_claude_resources()
    return all_dirs[0] if all_dirs else None


def extract_version(resources_dir: Path) -> str:
    """从 resources 目录路径中提取版本号"""
    parent_name = resources_dir.parent.name
    if parent_name.startswith("app-"):
        return parent_name[4:]
    return "未知版本"


def format_dir_size(path: Path) -> str:
    """获取目录大小并格式化为易读字符串"""
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        if total >= 1024 * 1024 * 1024:
            return f"{total / (1024 * 1024 * 1024):.1f} GB"
        elif total >= 1024 * 1024:
            return f"{total / (1024 * 1024):.0f} MB"
        elif total >= 1024:
            return f"{total / 1024:.0f} KB"
        return f"{total} B"
    except Exception:
        return "未知"


# ============================================================
#  Vite 风格交互式引导流程
# ============================================================


def run_vite_guided_flow(project_dir: Path, all_dirs: List[Path]) -> int:
    """
    Vite 风格交互式引导流程（线性流程）：
      选择操作 → 选择版本 → 确认执行
    """

    print(BANNER)
    print(f"  {BANNER_SUBTITLE}")
    print()

    # ===== 步骤 1: 选择操作 =====
    action = questionary.select(
        "请选择操作",
        choices=[
            questionary.Choice(title="安装汉化", value="install"),
            questionary.Choice(title="恢复英文原版", value="restore"),
        ],
        qmark="?",
        pointer="❯",
    ).unsafe_ask()

    is_restore = (action == "restore")
    action_label = "恢复英文原版" if is_restore else "安装汉化"

    # ===== 步骤 2: 选择目标版本 =====
    version_choices = []
    for res_dir in all_dirs:
        ver = extract_version(res_dir)
        sinicized = is_already_sinicized(res_dir)
        status = "已汉化" if sinicized else "未汉化"
        size = format_dir_size(res_dir.parent)
        label = f"v{ver}  ({status}, {size})"
        version_choices.append(
            questionary.Choice(title=label, value=("version", res_dir))
        )

    version_choices.append(
        questionary.Choice(title="手动输入 resources 目录路径", value=("manual", None))
    )

    result = questionary.select(
        "请选择目标版本",
        choices=version_choices,
        qmark="?",
        pointer="❯",
    ).unsafe_ask()

    kind, value = result

    if kind == "manual":
        # 用户选择手动输入路径
        manual_path_str = questionary.text(
            "请输入 resources 目录路径",
            validate=lambda text: _validate_manual_path(text),
            qmark="?",
        ).unsafe_ask()
        resources_dir = Path(manual_path_str.strip()).resolve()
        version_desc = f"手动指定: {resources_dir}"
    else:
        resources_dir = value
        ver = extract_version(resources_dir)
        sinicized = is_already_sinicized(resources_dir)
        status = "已汉化" if sinicized else "未汉化"
        version_desc = f"v{ver} ({status})"

    # ===== 步骤 3: 确认并执行 =====
    sinicized = is_already_sinicized(resources_dir)
    status_note = " (已汉化，将覆盖更新)" if sinicized else ""
    summary = (
        f"  操作: {action_label}\n"
        f"  目标: {version_desc}\n"
        f"  路径: {resources_dir}{status_note}"
    )

    print()
    print("  ── 确认信息 ─────────────────────────────")
    print(summary)
    print("  ──────────────────────────────────────────")
    print()

    confirmed = questionary.confirm(
        "确认执行？",
        default=True,
        qmark="?",
    ).unsafe_ask()

    if not confirmed:
        return 0

    print()
    print()
    print("=" * 50)
    if is_restore:
        success = restore_original(resources_dir)
    else:
        success = apply_patch(resources_dir, project_dir)
    print("=" * 50)
    if success:
        print(f"[{action_label} 完成]")
    else:
        print(f"[{action_label} 完成，但有错误]")
        return 1
    print("=" * 50)
    print()
    input("  按回车键退出...")
    return 0


def _validate_manual_path(text: str) -> bool:
    """校验手动输入的路径是否为有效的 resources 目录"""
    if not text.strip():
        return False
    p = Path(text.strip()).resolve()
    return (p / "en-US.json").is_file()


def run_fallback_guided_flow(project_dir: Path, all_dirs: List[Path]) -> int:
    """回退引导流程（当 questionary 不可用时，使用传统的数字选择）"""
    print(BANNER)
    print(f"  {BANNER_SUBTITLE}")
    print()
    print("  (questionary 库未安装，使用传统数字选择模式)")
    print()

    # 步骤 1: 选择操作
    print("  请选择操作：")
    print("          [1] 安装汉化")
    print("          [2] 恢复英文原版")

    while True:
        try:
            choice = input("  请选择 (1-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        try:
            idx = int(choice)
            if 1 <= idx <= 2:
                break
        except ValueError:
            pass
        print("  请输入 1 或 2。")

    is_restore = (idx == 2)
    action_label = "恢复英文原版" if is_restore else "安装汉化"

    # 步骤 2: 选择版本
    print()
    print("  请选择目标版本：")
    for i, res_dir in enumerate(all_dirs, 1):
        ver = extract_version(res_dir)
        sinicized = is_already_sinicized(res_dir)
        status = "已汉化" if sinicized else "未汉化"
        size = format_dir_size(res_dir.parent)
        print(f"    [{i}] v{ver}  ({status}, {size})")
    manual_idx = len(all_dirs) + 1
    print(f"    [{manual_idx}] 手动输入路径")

    while True:
        try:
            choice = input(f"  请选择 (1-{manual_idx}): ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        try:
            idx2 = int(choice)
            if 1 <= idx2 <= manual_idx:
                break
        except ValueError:
            pass
        print(f"  请输入 1-{manual_idx} 之间的数字。")

    if idx2 == manual_idx:
        try:
            manual_path = input("  请输入 resources 目录路径: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not manual_path or not _validate_manual_path(manual_path):
            print("  路径无效或未找到 en-US.json。")
            return 1
        resources_dir = Path(manual_path).resolve()
        version_desc = f"手动指定: {resources_dir}"
    else:
        resources_dir = all_dirs[idx2 - 1]
        ver = extract_version(resources_dir)
        sinicized = is_already_sinicized(resources_dir)
        status = "已汉化" if sinicized else "未汉化"
        version_desc = f"v{ver} ({status})"

    # 步骤 3: 确认
    sinicized = is_already_sinicized(resources_dir)
    status_note = " (已汉化，将覆盖更新)" if sinicized else ""
    print()
    print("  ── 确认信息 ─────────────────────────────")
    print("  操作: " + action_label)
    print("  目标: " + version_desc)
    print("  路径: " + str(resources_dir) + status_note)
    print("  ──────────────────────────────────────────")
    print()

    try:
        answer = input("  确认执行？[Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return 0
    if answer and answer not in ("y", "yes"):
        return 0

    # 执行
    print()
    print("=" * 50)
    if is_restore:
        success = restore_original(resources_dir)
    else:
        success = apply_patch(resources_dir, project_dir)
    print("=" * 50)
    if success:
        print(f"[{action_label} 完成]")
    else:
        print(f"[{action_label} 完成，但有错误]")
        return 1
    print("=" * 50)
    print()
    try:
        input("  按回车键退出...")
    except (EOFError, KeyboardInterrupt):
        pass
    return 0


def validate_json(path: Path) -> bool:
    """验证文件是否为合法 JSON"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"  [错误] JSON 解析失败: {path} -> {e}")
        return False


def backup_target(target: Path) -> bool:
    """备份目标文件，如果 .bak 已存在则跳过"""
    bak = target.with_suffix(target.suffix + ".bak")
    if bak.exists():
        print(f"  [备份] 已存在，跳过: {bak}")
        return True

    try:
        shutil.copy2(target, bak)
        print(f"  [备份] {target.name} -> {bak.name}")
        return True
    except Exception as e:
        print(f"  [错误] 备份失败: {target} -> {e}")
        return False


def install_patch(resources_dir: Path, project_dir: Path) -> bool:
    """执行汉化覆写"""
    print(f"\n目标目录: {resources_dir}")
    print(f"项目目录: {project_dir}")
    print("-" * 50)

    all_ok = True
    for src_rel, dst_rel in PATCH_MAP:
        src = project_dir / src_rel
        dst = resources_dir / dst_rel

        print(f"\n[{dst_rel}]")

        if not src.exists():
            print(f"  [跳过] 源文件不存在: {src}")
            continue

        if not dst.exists():
            print(f"  [跳过] 目标文件不存在: {dst}")
            continue

        if not validate_json(src):
            all_ok = False
            continue

        if not backup_target(dst):
            all_ok = False
            continue

        try:
            shutil.copy2(src, dst)
            print(f"  [覆写] {src.name} -> {dst}")
        except Exception as e:
            print(f"  [错误] 覆写失败: {dst} -> {e}")
            all_ok = False

    return all_ok


def restore_original(resources_dir: Path) -> bool:
    """从 .bak 恢复英文原版"""
    print(f"\n目标目录: {resources_dir}")
    print("-" * 50)

    all_ok = True
    for _, dst_rel in PATCH_MAP:
        dst = resources_dir / dst_rel
        bak = dst.with_suffix(dst.suffix + ".bak")

        print(f"\n[{dst_rel}]")

        if not bak.exists():
            print(f"  [跳过] 备份不存在: {bak}")
            continue

        try:
            shutil.copy2(bak, dst)
            print(f"  [恢复] {bak.name} -> {dst}")
        except Exception as e:
            print(f"  [错误] 恢复失败: {dst} -> {e}")
            all_ok = False

    return all_ok


def is_already_sinicized(resources_dir: Path) -> bool:
    """检查是否已经汉化（检测 en-US.json 中是否包含中文字符）"""
    en_us_path = resources_dir / "en-US.json"
    if not en_us_path.exists():
        return False
    try:
        with open(en_us_path, "r", encoding="utf-8") as f:
            for _ in range(64):
                line = f.readline()
                if not line:
                    break
                for ch in line:
                    if "一" <= ch <= "鿿":
                        return True
        return False
    except Exception:
        return False


def apply_patch(resources_dir: Path, project_dir: Path) -> bool:
    """应用汉化"""
    print(f"\n目标目录: {resources_dir}")
    print(f"项目目录: {project_dir}")
    print("-" * 50)

    if not install_patch(resources_dir, project_dir):
        return False

    print("汉化完成，请手动启动 Claude-Desktop。")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Claude-Desktop 跨平台汉化安装程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python install.py              # 交互式安装（方向键选择）
  python install.py --apply      # 快捷模式：跳过交互，安装并汉化
  python install.py --restore    # 快捷模式：跳过交互，恢复英文原版
  python install.py --path "C:\\Users\\...\\resources"  # 指定目录
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="手动指定 resources 目录（跳过引导流程）",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="从 .bak 备份恢复英文原版（跳过引导流程）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="安装汉化（跳过引导流程，直接处理最新版本）",
    )
    args = parser.parse_args()

    project_dir = get_project_dir()

    # 互斥参数检查
    if args.apply and args.restore:
        print("[错误] --apply 和 --restore 不能同时使用。")
        return 1

    # 判断是否为快捷模式（有明确指令，不走引导流程）
    is_quick_mode = args.path or args.apply or args.restore

    if not is_quick_mode:
        # ========== Vite 风格交互式引导 ==========
        all_dirs = find_all_claude_resources()
        if not all_dirs:
            print("[失败] 未找到 Claude-Desktop 安装路径。")
            print("        请使用 --path 手动指定 resources 目录。")
            print("        常见路径：")
            print("          Windows: %LOCALAPPDATA%\\AnthropicClaude\\app-{version}\\resources")
            print("          macOS:   /Applications/Claude.app/Contents/Resources")
            print("          Linux:   /usr/lib/claude-desktop/resources")
            return 1

        if HAS_QUESTIONARY:
            return run_vite_guided_flow(project_dir, all_dirs)
        else:
            return run_fallback_guided_flow(project_dir, all_dirs)

    # ========== 快捷模式 ==========
    # --path 模式：手动指定路径
    if args.path:
        resources_dir = args.path.resolve()
    else:
        # --apply / --restore 无 --path：自动选最新版本
        resources_dir = find_claude_resources()
        if not resources_dir:
            print("[失败] 未找到 Claude-Desktop 安装路径。")
            return 1

    if not (resources_dir / "en-US.json").is_file():
        print(f"[失败] 指定目录看起来不是有效的 resources 目录: {resources_dir}")
        return 1

    # 执行操作
    if args.restore:
        success = restore_original(resources_dir)
        action = "恢复英文原版"
    else:
        success = apply_patch(resources_dir, project_dir)
        action = "安装汉化"

    print("\n" + "=" * 50)
    if success:
        print(f"[{action}完成]")
    else:
        print(f"[{action}完成，但有错误]")
        return 1
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())