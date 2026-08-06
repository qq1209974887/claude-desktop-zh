#!/bin/bash
# Claude-Desktop 汉化安装脚本 (Bash)
# 用法:
#   chmod +x install.sh
#   ./install.sh              # 安装汉化
#   ./install.sh --apply      # 安装汉化
#   ./install.sh --restore    # 恢复英文原版
#   ./install.sh --path <dir> # 手动指定 resources 目录

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PATCH_MAP=(
  "resources/zh-CN.json:en-US.json"
  "resources/ion-dist/i18n/zh-CN.json:ion-dist/i18n/en-US.json"
  "resources/ion-dist/i18n/dynamic/zh-CN.json:ion-dist/i18n/dynamic/en-US.json"
)

# ANSI 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "  $*"; }
log_ok()    { echo -e "  ${GREEN}$*${NC}"; }
log_warn()  { echo -e "  ${YELLOW}$*${NC}"; }
log_error() { echo -e "  ${RED}$*${NC}"; }

find_resources_dir() {
  local manual_path="$1"
  if [[ -n "$manual_path" ]]; then
    echo "$manual_path"
    return
  fi

  local system="$(uname -s)"
  local candidates=()

  if [[ "$system" == "Darwin" ]]; then
    candidates+=(
      "/Applications/Claude.app/Contents/Resources"
      "$HOME/Applications/Claude.app/Contents/Resources"
    )
  elif [[ "$system" == "Linux" ]]; then
    candidates+=(
      "/usr/lib/claude-desktop/resources"
      "/opt/claude-desktop/resources"
      "$HOME/.local/lib/claude-desktop/resources"
      "/usr/share/claude-desktop/resources"
    )
  else
    # Windows / WSL
    local localappdata="${LOCALAPPDATA:-}"
    if [[ -z "$localappdata" ]]; then
      localappdata="$HOME/AppData/Local"
    fi
    local base="$localappdata/AnthropicClaude"
    if [[ -d "$base" ]]; then
      # 找最新的 app-* 目录
      local latest_dir=""
      for d in $(ls -d "$base"/app-* 2>/dev/null | sort -r); do
        local res="$d/resources"
        if [[ -d "$res" && -f "$res/en-US.json" ]]; then
          candidates+=("$res")
          break
        fi
      done
    fi
  fi

  for dir in "${candidates[@]}"; do
    if [[ -d "$dir" && -f "$dir/en-US.json" ]]; then
      echo "$dir"
      return
    fi
  done
  echo ""
}

is_already_sinicized() {
  local dir="$1"
  local enus="$dir/en-US.json"
  if [[ ! -f "$enus" ]]; then
    return 1
  fi
  # 检查前 64 行是否包含中文字符
  if head -n 64 "$enus" 2>/dev/null | grep -qP '[\x{4E00}-\x{9FFF}]'; then
    return 0
  fi
  return 1
}

backup_file() {
  local target="$1"
  local bak="${target}.bak"

  if [[ -f "$bak" ]]; then
    log_info "[备份] 已存在，跳过: $(basename "$bak")"
    return 0
  fi

  cp -f "$target" "$bak" 2>/dev/null
  if [[ $? -eq 0 ]]; then
    log_ok "[备份] $(basename "$target") -> $(basename "$bak")"
    return 0
  else
    log_error "[错误] 备份失败: $target"
    return 1
  fi
}

install_patch() {
  local resources_dir="$1"

  echo ""
  log_info "目标目录: $resources_dir"
  log_info "项目目录: $PROJECT_DIR"
  echo -e "  $(printf -- '-%.0s' {1..50})"

  local all_ok=true
  for mapping in "${PATCH_MAP[@]}"; do
    local src_rel="${mapping%%:*}"
    local dst_rel="${mapping##*:}"
    local src="$PROJECT_DIR/$src_rel"
    local dst="$resources_dir/$dst_rel"

    echo ""
    log_info "[$dst_rel]"

    if [[ ! -f "$src" ]]; then
      log_warn "[跳过] 源文件不存在: $src_rel"
      continue
    fi
    if [[ ! -f "$dst" ]]; then
      log_warn "[跳过] 目标文件不存在: $dst_rel"
      continue
    fi

    # 校验 JSON（简单检查：文件非空且以 { 开头）
    if [[ ! -s "$src" ]] || [[ "$(head -c1 "$src" 2>/dev/null)" != "{" ]]; then
      log_error "[错误] JSON 文件无效或为空: $src_rel"
      all_ok=false
      continue
    fi

    if ! backup_file "$dst"; then
      all_ok=false
      continue
    fi

    cp -f "$src" "$dst" 2>/dev/null
    if [[ $? -eq 0 ]]; then
      log_ok "[覆写] $(basename "$src") -> $dst_rel"
    else
      log_error "[错误] 覆写失败: $dst"
      all_ok=false
    fi
  done

  $all_ok && return 0 || return 1
}

restore_original() {
  local resources_dir="$1"

  echo ""
  log_info "目标目录: $resources_dir"
  echo -e "  $(printf -- '-%.0s' {1..50})"

  local all_ok=true
  for mapping in "${PATCH_MAP[@]}"; do
    local dst_rel="${mapping##*:}"
    local dst="$resources_dir/$dst_rel"
    local bak="${dst}.bak"

    echo ""
    log_info "[$dst_rel]"

    if [[ ! -f "$bak" ]]; then
      log_warn "[跳过] 备份不存在"
      continue
    fi

    cp -f "$bak" "$dst" 2>/dev/null
    if [[ $? -eq 0 ]]; then
      log_ok "[恢复] $(basename "$bak") -> $(basename "$dst")"
    else
      log_error "[错误] 恢复失败: $dst"
      all_ok=false
    fi
  done

  $all_ok && return 0 || return 1
}

apply_patch() {
  local resources_dir="$1"

  echo ""
  log_info "目标目录: $resources_dir"
  log_info "项目目录: $PROJECT_DIR"
  echo -e "  $(printf -- '-%.0s' {1..50})"

  install_patch "$resources_dir"
  local patch_ok=$?

  if [[ $patch_ok -eq 0 ]]; then
    log_ok "汉化完成，请手动启动 Claude-Desktop。"
  fi
  return $patch_ok
}

# ============== 主入口 ==============

MANUAL_PATH=""
RESTORE=false
APPLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      MANUAL_PATH="$2"
      shift 2
      ;;
    --restore)
      RESTORE=true
      shift
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    *)
      echo "未知参数: $1"
      echo "用法: ./install.sh [--path <dir>] [--restore] [--apply]"
      exit 1
      ;;
  esac
done

if $APPLY && $RESTORE; then
  echo -e "${RED}[错误] --apply 和 --restore 不能同时使用。${NC}"
  exit 1
fi

echo "=================================================="
echo "  Claude-Desktop 汉化安装程序 (Bash)"
echo "=================================================="

RESOURCES_DIR="$(find_resources_dir "$MANUAL_PATH")"

if [[ -z "$RESOURCES_DIR" ]]; then
  echo -e "\n${RED}[失败] 未找到 Claude-Desktop 安装路径。${NC}"
  echo -e "${YELLOW}       请使用 --path 参数手动指定 resources 目录。${NC}"
  echo -e "${YELLOW}       常见路径：${NC}"
  echo -e "${YELLOW}         macOS:   /Applications/Claude.app/Contents/Resources${NC}"
  echo -e "${YELLOW}         Linux:   /usr/lib/claude-desktop/resources${NC}"
  echo -e "${YELLOW}         Windows: %LOCALAPPDATA%/AnthropicClaude/app-*/resources${NC}"
  exit 1
fi

log_info "探测到的 resources 目录: $RESOURCES_DIR"

if $RESTORE; then
  SUCCESS=true
  restore_original "$RESOURCES_DIR" || SUCCESS=false
  ACTION="恢复"
elif $APPLY; then
  SUCCESS=true
  apply_patch "$RESOURCES_DIR" || SUCCESS=false
  ACTION="汉化应用"
else
  SUCCESS=true
  install_patch "$RESOURCES_DIR" || SUCCESS=false
  ACTION="汉化安装"
fi

echo ""
echo "=================================================="
if $SUCCESS; then
  echo -e "  ${GREEN}[$ACTION 完成]${NC}"
  if ! $RESTORE && ! $APPLY; then
    log_info "安装完成后，请手动启动 Claude-Desktop。"
  fi
else
  echo -e "  ${YELLOW}[$ACTION 完成，但有错误]${NC}"
fi
echo "=================================================="

if $SUCCESS; then
  # 等待用户确认后退出
  echo ""
  read -p "  按回车键退出... " _
fi

exit $([ "$SUCCESS" = true ] && echo 0 || echo 1)