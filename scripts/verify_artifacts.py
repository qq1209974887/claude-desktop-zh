#!/usr/bin/env python3
"""
验证 GitHub Actions 构建产物的完整性

用法:
    python scripts/verify_artifacts.py <产物目录或 zip 文件>
    python scripts/verify_artifacts.py dist/
    python scripts/verify_artifacts.py claude-zh-patch-linux.zip

功能:
    1. 自动识别产物类型（Windows .exe / Linux ELF / macOS Mach-O）
    2. 检查目录结构完整性（resources、src、使用说明.md）
    3. 校验二进制 magic number（ELF 0x7F454c46，Mach-O）
    4. 检查文件大小是否合理（PyInstaller 产物通常 > 10MB）

注意:
    本脚本仅进行静态验证，不执行二进制文件。
    要验证可执行性，请在对应平台运行文件。
"""

import argparse
import os
import struct
import sys
import zipfile
from pathlib import Path


EXPECTED_FILES = [
    "resources/zh-CN.json",
    "resources/ion-dist/i18n/zh-CN.json",
    "resources/ion-dist/i18n/dynamic/zh-CN.json",
    "src/install.py",
    "使用说明.md",
]

MIN_EXEC_SIZE = 5 * 1024 * 1024  # 5MB，PyInstaller 单文件一般远大于此

# ELF magic: \x7fELF
ELF_MAGIC = b"\x7fELF"
# Mach-O magic numbers (32-bit and 64-bit, big/little endian)
MACHO_MAGICS = {
    0xFEEDFACE: "Mach-O 32-bit",
    0xFEEDFACF: "Mach-O 64-bit",
    0xCEFAEDFE: "Mach-O 32-bit (swap)",
    0xCFFAEDFE: "Mach-O 64-bit (swap)",
    0xCAFEBABE: "Fat Mach-O (32-bit)",
    0xCAFEBABF: "Fat Mach-O (64-bit)",
    0xBEBAFECA: "Fat Mach-O (swap)",
}


def detect_platform(filepath: Path) -> str:
    """通过文件扩展名和 magic number 识别二进制文件平台"""
    name_lower = filepath.name.lower()

    if name_lower.endswith(".exe"):
        return "windows"

    try:
        with open(filepath, "rb") as f:
            head = f.read(16)
    except (OSError, IOError):
        return "unknown"

    if head.startswith(ELF_MAGIC):
        # ELF class: 1 = 32-bit, 2 = 64-bit
        if len(head) >= 5 and head[4] == 2:
            return "linux_64"
        return "linux_32"

    if len(head) >= 4:
        magic = struct.unpack(">I", head[:4])[0]
        if magic in MACHO_MAGICS:
            return MACHO_MAGICS[magic]

        # Try little-endian
        magic_le = struct.unpack("<I", head[:4])[0]
        if magic_le in MACHO_MAGICS:
            return MACHO_MAGICS[magic_le]

    return "unknown"


def find_binary(directory: Path) -> Path | None:
    """在目录中查找可执行文件"""
    candidates = []
    for f in directory.iterdir():
        if f.is_file():
            lower = f.name.lower()
            if lower.startswith("claude-zh-patch"):
                candidates.append(f)

    if not candidates:
        # Fallback: 找第一个较大的文件
        for f in directory.iterdir():
            if f.is_file() and f.stat().st_size > MIN_EXEC_SIZE:
                candidates.append(f)
                break

    return candidates[0] if candidates else None


def verify_extracted_dir(dirpath: Path) -> list[str]:
    """验证解压后的产物目录"""
    issues = []
    print(f"\n验证目录: {dirpath}")
    print("=" * 50)

    # 1. 查找二进制文件
    binary = find_binary(dirpath)
    if binary is None:
        print("[FAIL] 未找到可执行文件")
        issues.append("no binary found")
        return issues

    print(f"\n二进制文件: {binary.name}")
    size_mb = binary.stat().st_size / (1024 * 1024)
    print(f"  大小: {size_mb:.1f} MB")

    # 2. 检查平台
    platform = detect_platform(binary)
    print(f"  平台识别: {platform}")

    expected_platform = None
    name = binary.name.lower()
    if name.endswith(".exe"):
        expected_platform = "windows"
    elif "linux" in str(dirpath).lower():
        expected_platform = "linux"
    elif "macos" in str(dirpath).lower() or "darwin" in str(dirpath).lower():
        expected_platform = "macos"

    if expected_platform and expected_platform not in platform.lower():
        print(f"  [WARN] 平台可能不匹配：期望 {expected_platform}，检测为 {platform}")
        issues.append(f"platform mismatch: expected {expected_platform}, got {platform}")
    else:
        print(f"  [PASS] 平台识别正常")

    # 3. 检查文件大小
    if binary.stat().st_size < MIN_EXEC_SIZE:
        print(f"  [FAIL] 文件过小 ({size_mb:.1f} MB)，可能打包不完整")
        issues.append(f"too small: {size_mb:.1f} MB")
    else:
        print(f"  [PASS] 文件大小合理")

    # 4. 检查资源文件
    print(f"\n资源文件检查:")
    for rel_path in EXPECTED_FILES:
        full_path = dirpath / rel_path
        if full_path.exists():
            print(f"  [PASS] {rel_path}")
        else:
            print(f"  [FAIL] {rel_path} 缺失")
            issues.append(f"missing: {rel_path}")

    # 5. 检查 logs
    logs_dir = dirpath / "logs"
    if logs_dir.is_dir():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            print(f"\n日志文件: {len(log_files)} 个")
            for lf in log_files:
                print(f"  - {lf.name} ({lf.stat().st_size} bytes)")
    else:
        print(f"\n[WARN] logs/ 目录不存在")

    return issues


def verify_zip(zippath: Path) -> list[str]:
    """验证 zip 压缩包"""
    issues = []
    print(f"\n验证 zip: {zippath}")
    print("=" * 50)

    try:
        with zipfile.ZipFile(zippath, "r") as zf:
            names = zf.namelist()
            print(f"\n文件数: {len(names)}")

            # 列出二进制文件
            for name in names:
                basename = os.path.basename(name).lower()
                if basename.startswith("claude-zh-patch") and not basename.endswith(".py"):
                    info = zf.getinfo(name)
                    print(f"  二进制: {name} ({info.file_size / 1024 / 1024:.1f} MB)")

            # 检查关键文件
            print(f"\n关键文件检查:")
            basenames = [os.path.basename(n).lower() for n in names]

            for expected in ["zh-cn.json", "install.py", "使用说明.md"]:
                found = any(expected in bn for bn in basenames)
                if found:
                    print(f"  [PASS] 包含 {expected}")
                else:
                    print(f"  [FAIL] 缺少 {expected}")
                    issues.append(f"missing in zip: {expected}")

            # 验证 zip 完整性
            bad_file = zf.testzip()
            if bad_file is None:
                print(f"\n[PASS] zip 完整性校验通过")
            else:
                print(f"\n[FAIL] zip 损坏：{bad_file}")
                issues.append("corrupted zip")
    except zipfile.BadZipFile as e:
        print(f"[FAIL] zip 文件损坏: {e}")
        issues.append(f"bad zip: {e}")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="验证 GitHub Actions 构建产物的完整性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python scripts/verify_artifacts.py dist/
  python scripts/verify_artifacts.py claude-zh-patch-linux.zip
  python scripts/verify_artifacts.py ./downloaded-artifacts/
""",
    )
    parser.add_argument("path", help="产物目录路径或 zip 文件路径")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="递归验证目录下所有子目录"
    )
    parser.add_argument(
        "--extracted-only",
        action="store_true",
        help="仅验证已解压的目录（跳过 zip）",
    )
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.exists():
        print(f"[错误] 路径不存在: {target}")
        sys.exit(1)

    all_issues = []

    if target.is_file() and target.suffix == ".zip":
        # 验证单个 zip
        all_issues.extend(verify_zip(target))
    elif target.is_dir():
        if args.recursive:
            # 递归：验证每个子目录及 zip
            for child in sorted(target.iterdir()):
                if child.is_dir():
                    issues = verify_extracted_dir(child)
                    all_issues.extend(issues)
                elif child.suffix == ".zip":
                    issues = verify_zip(child)
                    all_issues.extend(issues)
        else:
            # 直接验证当前目录
            issues = verify_extracted_dir(target)
            all_issues.extend(issues)

            # 同时检查 zip
            for zip_file in target.glob("*.zip"):
                issues = verify_zip(zip_file)
                all_issues.extend(issues)
    else:
        print(f"[错误] 不支持的文件类型: {target}")
        sys.exit(1)

    # 汇总
    print(f"\n{'=' * 50}")
    print(f"验证汇总:")
    print(f"  发现问题: {len(all_issues)} 项")
    if all_issues:
        for issue in all_issues:
            print(f"    - {issue}")
        print(f"\n[结果] ❌ 未通过")
        sys.exit(1)
    else:
        print(f"\n[结果] ✅ 全部通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
