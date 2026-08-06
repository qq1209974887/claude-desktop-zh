# Claude Desktop 汉化补丁程序 - 使用说明

> 本指南将详细介绍如何轻松将 Claude Desktop 界面汉化为中文。

---

## 一、快速汉化方式

双击运行 `claude-zh-patch.exe`，它会弹出一个终端窗口，然后根据提示进行操作。安装完成后，手动启动 Claude Desktop 即可看到中文界面。

## 二、汉化操作指南

### 1、命令行方式

如果你更习惯命令行，可以在终端中运行：

#### macOS / Linux (Bash)

```bash
chmod +x src/install.sh
./src/install.sh
./src/install.sh --apply
./src/install.sh --restore
```

#### 所有平台 (依赖 Python 环境)

```bash
python src/install.py
python src/install.py --apply
python src/install.py --restore
```

运行后，脚本会自动查找 Claude Desktop 安装位置，并以交互式问答的方式引导你完成安装。

> 需要预先安装 Python 环境（包含 `questionary` 库）。

---

## 三、命令行方式进阶

| 需求 | 命令 | 说明 |
| ------ | ------ | ------ |
| **一键安装** | `--apply` | 跳过交互，直接安装汉化包 |
| **恢复英文** | `--restore` | 将界面恢复为原始的英文版本 |
| **指定路径** | `--path <目录>` | 自动探测失败时手动指定 Claude 安装目录 |
| **帮助** | `--help` | 显示帮助信息 |

**示例：**

```bash
# 一键安装（最省事）
claude-zh-patch.exe --apply

# 恢复英文
claude-zh-patch.exe --restore
```

---

## 四、安装方式对比

| 方式 | Windows | macOS | Linux | 说明 |
| ------ | :---: | :---: | :---: | ------ |
| **exe 双击运行** | ✅ | ✅ | ✅ | 最简单，无需配置环境 |
| **Python 脚本** | ⚠️ | ⚠️ | ⚠️ | 需要 Python 环境 |
| **Bash 脚本** | ⚠️ | ✅ | ✅ | Windows 需 WSL/Git Bash |

- ✅ 完全支持
- ⚠️ 需要额外工具

---

## 五、备份与恢复机制

- **自动备份**：首次安装时，程序会自动将原始英文文件备份为 `.bak` 文件
- **恢复**：运行 `--restore` 即可从备份恢复英文界面
- **安全**：备份文件仅在首次安装时创建，后续更新不会覆盖备份

---

## 六、常见问题

**Q: 安装后部分界面仍是英文？**
A: 请确认你的汉化包版本与 Claude Desktop 版本匹配。新版 Claude Desktop 可能需要更新的汉化文件。

**Q: 如何确认是否已安装成功？**
A: 打开 Claude Desktop，如果看到「新对话」、「设置」等中文菜单，则表示安装成功。

**Q: 安装失败或路径探测不到？**
A: 可以使用 `--path` 参数手动指定。常见路径：

- Windows: `%LOCALAPPDATA%\AnthropicClaude\app-xxx\resources`
- macOS: `/Applications/Claude.app/Contents/Resources`

**Q: 如何卸载汉化补丁？**
A: 无需卸载。直接运行 `claude-zh-patch.exe --restore` 即可恢复英文。
