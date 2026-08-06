#!/usr/bin/env python3
"""
编译跨平台可执行文件的脚本

用法:
    python build_exes.py                  # 尝试编译所有平台（自动检测环境，不匹配则跳过）
    python build_exes.py windows          # 仅编译 Windows .exe
    python build_exes.py macos            # 仅编译 macOS 可执行文件（需 Mac）
    python build_exes.py linux            # 仅编译 Linux 可执行文件（需 Linux）
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并打印输出"""
    print(f"$ {' '.join(str(x) for x in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if result.returncode != 0:
        print(f"[错误] 命令失败，退出码：{result.returncode}")
        return False
    return True


def copy_extras(project_dir: Path, output_dir: Path) -> list:
    """
    复制命令行安装脚本、resources 和 README 到 dist 目录，
    让打包成品同时包含「可执行文件」和「命令行安装」两种使用方式。
    返回已复制文件的描述列表。
    """
    import shutil

    copied: list = []

    # 1. 复制 DESCRIPTION.md -> 使用说明.md（面向终端用户）
    desc_file = project_dir / "DESCRIPTION.md"
    if desc_file.exists():
        shutil.copy(desc_file, output_dir / "使用说明.md")
        copied.append("使用说明.md")

    # 2. 复制 src/ 目录（命令行安装脚本）
    src_dir = project_dir / "src"
    dst_src = output_dir / "src"
    if src_dir.exists():
        if dst_src.exists():
            shutil.rmtree(dst_src)
        shutil.copytree(src_dir, dst_src)
        copied.append("src/（命令行安装脚本）")

    # 3. 复制 resources/ 目录（翻译文件，命令行脚本运行时需要）
    res_dir = project_dir / "resources"
    dst_res = output_dir / "resources"
    if res_dir.exists():
        if dst_res.exists():
            shutil.rmtree(dst_res)
        shutil.copytree(res_dir, dst_res)
        copied.append("resources/（翻译文件）")

    return copied


def get_platform():
    """获取当前平台标识"""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    else:
        return "linux"


ALL_PLATFORMS = ["windows", "macos", "linux"]


def check_environment(platform):
    """检测当前系统环境是否适合构建指定平台"""
    current = get_platform()
    if current != platform:
        print(f"  [跳过] 当前系统为 {current}，无法为 {platform} 构建（PyInstaller 不支持交叉编译）")
        return False
    return True


def cleanup_build_artifacts(project_dir: Path) -> None:
    """清理 PyInstaller 打包过程产物"""
    import shutil

    # 1. 清理中间目录 build/build_temp/
    workpath = project_dir / "build" / "build_temp"
    if workpath.exists():
        shutil.rmtree(workpath)
        print("  [清理] 已移除中间目录: build/build_temp/")

    # 2. 清理 .spec 文件
    for spec in project_dir.glob("*.spec"):
        spec.unlink()
        print(f"  [清理] 已移除: {spec.name}")


def build_for_platform(platform=None):
    """为指定平台构建可执行文件；若 platform 为 None 则尝试构建所有平台（环境不合格则跳过）"""

    project_dir = Path(__file__).parent.parent.resolve()

    if platform is None:
        # 无参数：遍历所有平台，逐一检测环境后构建
        results = {}
        for plat in ALL_PLATFORMS:
            print(f"\n{'─' * 40}")
            print(f"尝试构建 {plat} 平台...")
            if not check_environment(plat):
                results[plat] = "skip"
                continue
            ok = _build_single_platform(plat, project_dir)
            results[plat] = "ok" if ok else "fail"

        # 打印汇总
        print(f"\n{'=' * 50}")
        print("构建汇总：")
        for plat, status in results.items():
            if status == "ok":
                print(f"  ✓ {plat}：构建成功")
            elif status == "skip":
                print(f"  ⊘ {plat}：已跳过（环境不匹配）")
            else:
                print(f"  ✗ {plat}：构建失败")
        print("=" * 50)

        return all(s == "ok" or s == "skip" for s in results.values())

    # 指定了单个平台
    if not check_environment(platform):
        return False
    return _build_single_platform(platform, project_dir)


def _build_single_platform(platform, project_dir):
    """为指定平台（已验证环境）执行实际构建"""
    if platform == "windows":
        return build_windows(project_dir)
    elif platform == "macos":
        return build_macos(project_dir)
    elif platform == "linux":
        return build_linux(project_dir)
    else:
        print(f"[错误] 不支持的平台：{platform}")
        return False


def build_windows(project_dir):
    """Windows - 生成单文件.exe"""

    output_dir = project_dir / "dist"

    # 清理旧的 dist 文件夹
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print("清除了旧的 dist 目录")

    # PyInstaller 命令参数（单文件模式）
    # Windows 使用 ; 作为 --add-data 的分隔符
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",                    # 单文件
        "--name", "claude-zh-patch",     # 输出文件名
        "--workpath", str(project_dir / "build" / "build_temp"),  # 中间文件位置
        "--distpath", str(output_dir),   # 输出位置
        "--console",                     # 保留控制台窗口（用于显示进度）
        "--icon", "NONE",               # 无图标（大写 NONE 表示不使用图标）
        "--add-data", f"{project_dir}/resources;resources",  # 嵌入翻译资源（Windows 使用 ; 分隔）
        "--hidden-import", "json",      # 确保 json 模块被包含
        "--hidden-import", "questionary",  # 交互式选择库
        str(project_dir / "src" / "install.py"),
    ]

    # 在 Windows 上还需要添加 --upx-dir 如果可用来压缩 exe
    # 默认安装 PyInstaller 会尝试自动使用 UPX

    print("\n开始编译 Windows 版本...")
    if not run_command(cmd):
        return False

    # 检查是否生成成功
    exe = output_dir / "claude-zh-patch.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n[完成] Windows 可执行文件已生成：{exe}")
        print(f"大小：{size_mb:.1f} MB")

        # 复制附加文件到 dist，让成品同时包含命令行安装方式
        import shutil
        extras = copy_extras(project_dir, output_dir)
        for desc in extras:
            print(f"  [附加] {desc}")

        # 清理过程产物
        cleanup_build_artifacts(project_dir)

        return True
    else:
        print("[错误] 编译后未找到可执行文件")
        return False


def build_macos(project_dir):
    """macOS - 生成 Mach-O 二进制文件"""

    output_dir = project_dir / "dist"

    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    # macOS 使用 : 作为 --add-data 的分隔符
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",
        "--name", "claude-zh-patch",
        "--workpath", str(project_dir / "build" / "build_temp"),
        "--distpath", str(output_dir),
        "--console",
        "--add-data", f"{project_dir}/resources:resources",
        "--hidden-import", "json",
        "--hidden-import", "questionary",
        str(project_dir / "src" / "install.py"),
    ]

    print("\n开始编译 macOS 版本...")
    if not run_command(cmd):
        return False

    binary = output_dir / "claude-zh-patch"
    if binary.exists():
        chmod_cmd = ["chmod", "+x", str(binary)]
        run_command(chmod_cmd)

        size_mb = binary.stat().st_size / (1024 * 1024)
        print(f"\n[完成] macOS 可执行文件已生成：{binary}")
        print(f"大小：{size_mb:.1f} MB")

        # 复制附加文件到 dist
        extras = copy_extras(project_dir, output_dir)
        for desc in extras:
            print(f"  [附加] {desc}")

        # 清理过程产物
        cleanup_build_artifacts(project_dir)

        return True
    else:
        print("[错误] 编译后未找到可执行文件")
        return False


def build_linux(project_dir):
    """Linux - 生成 ELF 二进制文件"""

    output_dir = project_dir / "dist"

    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",
        "--name", "claude-zh-patch",
        "--workpath", str(project_dir / "build" / "build_temp"),
        "--distpath", str(output_dir),
        "--console",
        "--add-data", f"{project_dir}/resources:resources",
        "--hidden-import", "json",
        "--hidden-import", "questionary",
        str(project_dir / "src" / "install.py"),
    ]

    print("\n开始编译 Linux 版本...")
    if not run_command(cmd):
        return False

    elf = output_dir / "claude-zh-patch"
    if elf.exists():
        chmod_cmd = ["chmod", "+x", str(elf)]
        run_command(chmod_cmd)

        size_mb = elf.stat().st_size / (1024 * 1024)
        print(f"\n[完成] Linux 可执行文件已生成：{elf}")
        print(f"大小：{size_mb:.1f} MB")

        # 复制附加文件到 dist，让成品同时包含命令行安装方式
        extras = copy_extras(project_dir, output_dir)
        for desc in extras:
            print(f"  [附加] {desc}")

        # 清理过程产物
        cleanup_build_artifacts(project_dir)

        return True
    else:
        print("[错误] 编译后未找到可执行文件")
        return False


def print_help():
    """打印帮助信息"""
    help_text = """\
Claude-Desktop 汉化程序 - 跨平台编译脚本

用法:
    python build/build_exes.py [平台]

参数:
    平台    指定目标平台，可选值：
              windows    仅编译 Windows .exe
              macos      仅编译 macOS 可执行文件（需在 Mac 上运行）
              linux      仅编译 Linux 可执行文件（需在 Linux 上运行）
            省略该参数时，将依次尝试为所有平台构建，
            环境不匹配的平台会自动跳过。

选项:
    -h, --help    显示此帮助信息并退出

示例:
    python build/build_exes.py                  # 为所有平台构建（自动检测环境）
    python build/build_exes.py windows          # 仅构建 Windows 版本
    python build/build_exes.py macos            # 仅构建 macOS 版本
    python build/build_exes.py linux            # 仅构建 Linux 版本

说明:
    · PyInstaller 不支持交叉编译，必须在目标平台上执行对应平台的构建。
    · 输出位置：dist/claude-zh-patch[.exe]
    · 构建完成后，附加文件（使用说明.md、src/、resources/）会被复制到 dist/。
"""
    print(help_text)


def main():
    """主入口"""

    # 解析参数
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        print_help()
        sys.exit(0)

    print("=" * 50)
    print("Claude-Desktop 汉化程序 - 编译脚本")
    print("=" * 50)
    print()
    print(f"当前平台：{get_platform()}")
    print(f"Python 版本：{sys.version.split()[0]}")
    print()

    # 检查依赖
    try:
        import PyInstaller
        print(f"✓ PyInstaller 已安装 (版本 {PyInstaller.__version__})")
    except ImportError:
        print("✗ PyInstaller 未安装")
        print("请运行：pip install pyinstaller")
        return False

    platform = None
    if argv:
        platform = argv[0].lower()

    if platform and platform not in ALL_PLATFORMS:
        print(f"[错误] 不支持的平台：{platform}")
        print(f"可选值：{', '.join(ALL_PLATFORMS)}")
        print("使用 -h 或 --help 查看完整帮助。")
        return False

    if platform is None:
        print("\n模式：尝试为所有平台构建（环境不合格的将自动跳过）")
    else:
        print(f"\n模式：仅为 {platform} 平台构建")

    success = build_for_platform(platform)

    if success:
        print("\n全部完成！可执行文件位于：dist/claude-zh-patch*")
        sys.exit(0)
    else:
        print("\n构建过程中存在失败项，请查看上方汇总。")
        sys.exit(1)


if __name__ == "__main__":
    main()
