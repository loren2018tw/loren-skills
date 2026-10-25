#!/usr/bin/env bash
#
# 將本倉庫的技能與 OpenCode agents 以檔案系統連結安裝到目標位置。
# 技能目錄連結到目標技能庫；agent .md 與輔助腳本逐檔連結到 OpenCode 設定根目錄。
# 連結安裝＝本倉庫更新即時反映；--uninstall 可完整還原。
#
# 用法: ./install.sh [--target DIR] [--opencode-dir DIR] [--agents] [--skills]
#                    [--uninstall] [--dry-run] [--force] [技能或 agent 名稱...]

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

TARGET=""
OPENCODE_DIR=""
UNINSTALL=0
DRY_RUN=0
FORCE=0
FLAG_AGENTS=0
FLAG_SKILLS=0
WANTED=()

created=0 updated=0 unchanged=0 backed=0 pruned=0 removed=0 failed=0

die() { printf '[錯誤] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
用法: ./install.sh [選項] [技能或 agent 名稱...]

將本倉庫的技能目錄連結到目標技能庫，並把 OpenCode agents 與輔助腳本
逐檔連結到 OpenCode 設定根目錄的 agents/ 與 bin/。
之後在本倉庫 git pull，OpenCode 端即時生效，無需重裝。

選項:
  --target DIR       技能安裝位置（預設 ~/.agents/skills）
  --opencode-dir DIR OpenCode 設定根目錄（預設 OPENCODE_CONFIG_DIR、
                     $XDG_CONFIG_HOME/opencode 或 ~/.config/opencode）
  --agents           只處理 OpenCode agents（含 bin 輔助腳本）
  --skills           只處理技能
  --uninstall        移除本倉庫建立的連結（可搭配名稱或 --agents／--skills）
  --dry-run          只預覽動作，不做任何修改
  --force            目標已有非本倉庫項目時，先備份成 <名稱>.bak-<時間戳> 再連結
  -h, --help         顯示本說明

不帶名稱＝全量安裝（技能＋agents；並清除陳舊連結）。
指定名稱＝只處理這些項目；agent 會一併安裝 bin/ 下的輔助腳本。

範例:
  ./install.sh                        # 全量安裝
  ./install.sh --agents               # 只安裝 agents 與輔助腳本
  ./install.sh geminiimage            # 只安裝指定 agent（含輔助腳本）
  ./install.sh --skills who-is-loren  # 只安裝指定技能
  ./install.sh --uninstall --agents   # 只移除 agents 與輔助腳本
  ./install.sh --dry-run              # 預覽全量安裝
EOF
}

# ---- 平台檢查 ---------------------------------------------------------------
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    die "偵測到 Git Bash／MSYS／Cygwin：ln -s 在這些環境不是真正的連結，請改用 Windows PowerShell 執行 install.ps1。"
    ;;
esac

# ---- 路徑工具 ---------------------------------------------------------------
abs_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$PWD" "$1" ;;
  esac
}

strip_slash() {
  local p="$1"
  while [ "${p%/}" != "$p" ]; do p="${p%/}"; done
  printf '%s\n' "$p"
}

path_under() { # $1=路徑 $2=基底；路徑等於基底或其子路徑時成功
  case "$1" in
    "$2"|"$2"/*) return 0 ;;
  esac
  return 1
}

link_target_abs() { # $1=連結；印出絕對目標路徑
  local link="$1" target
  target="$(readlink "$link" 2>/dev/null)" || return 1
  case "$target" in
    /*) : ;;
    *) target="$(cd -- "$(dirname -- "$link")" && pwd -P)/${target#./}" ;;
  esac
  printf '%s\n' "$target"
}

# ---- 解析參數 ---------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      [ $# -ge 2 ] || die "--target 需要一個目錄參數"
      TARGET="$2"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --opencode-dir)
      [ $# -ge 2 ] || die "--opencode-dir 需要一個目錄參數"
      OPENCODE_DIR="$2"; shift 2 ;;
    --opencode-dir=*) OPENCODE_DIR="${1#*=}"; shift ;;
    --agents|--only-agents) FLAG_AGENTS=1; shift ;;
    --skills|--only-skills) FLAG_SKILLS=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --)
      shift
      while [ $# -gt 0 ]; do WANTED+=("$1"); shift; done ;;
    -*) die "未知旗標：$1（用 --help 看用法）" ;;
    *) WANTED+=("$1"); shift ;;
  esac
done

if [ "$FLAG_AGENTS" -eq 0 ] && [ "$FLAG_SKILLS" -eq 0 ]; then
  SEL_AGENTS=1
  SEL_SKILLS=1
else
  SEL_AGENTS=$FLAG_AGENTS
  SEL_SKILLS=$FLAG_SKILLS
fi

# ---- 目標路徑 ---------------------------------------------------------------
if [ "$SEL_SKILLS" -eq 1 ]; then
  if [ -z "$TARGET" ]; then
    [ -n "${HOME:-}" ] || die "找不到 HOME，請用 --target 指定安裝位置"
    TARGET="$HOME/.agents/skills"
  fi
  TARGET="$(strip_slash "$(abs_path "$TARGET")")"
  [ -n "$TARGET" ] || die "目標技能庫路徑不合法"
  case "$TARGET" in
    "$ROOT"|"$ROOT"/*) die "目標技能庫不能位於本倉庫內：$TARGET" ;;
  esac
  if [ -e "$TARGET" ] && [ ! -d "$TARGET" ]; then
    die "目標技能庫不是目錄：$TARGET"
  fi
fi

AGENT_SRC="$ROOT/opencode/agents"
BIN_SRC="$ROOT/opencode/bin"
AGENTS_TARGET=""
BIN_TARGET=""

if [ "$SEL_AGENTS" -eq 1 ]; then
  if [ -z "$OPENCODE_DIR" ]; then
    if [ -n "${OPENCODE_CONFIG_DIR:-}" ]; then
      OPENCODE_DIR="$OPENCODE_CONFIG_DIR"
    elif [ -n "${XDG_CONFIG_HOME:-}" ]; then
      OPENCODE_DIR="$XDG_CONFIG_HOME/opencode"
    else
      [ -n "${HOME:-}" ] || die "找不到 HOME，請用 --opencode-dir 指定 OpenCode 設定根目錄"
      OPENCODE_DIR="$HOME/.config/opencode"
    fi
  fi
  OPENCODE_DIR="$(strip_slash "$(abs_path "$OPENCODE_DIR")")"
  [ -n "$OPENCODE_DIR" ] || die "OpenCode 設定根目錄路徑不合法"
  case "$OPENCODE_DIR" in
    "$ROOT"|"$ROOT"/*) die "OpenCode 設定根目錄不能位於本倉庫內：$OPENCODE_DIR" ;;
  esac
  if [ -e "$OPENCODE_DIR" ] && [ ! -d "$OPENCODE_DIR" ]; then
    die "OpenCode 設定根目錄不是目錄：$OPENCODE_DIR"
  fi
  AGENTS_TARGET="$OPENCODE_DIR/agents"
  BIN_TARGET="$OPENCODE_DIR/bin"
  for d in "$AGENTS_TARGET" "$BIN_TARGET"; do
    if [ -e "$d" ] && [ ! -d "$d" ]; then
      die "OpenCode 目標不是目錄：$d"
    fi
  done
  if [ "$SEL_SKILLS" -eq 1 ] && [ "$TARGET" = "$OPENCODE_DIR" ]; then
    die "技能目標與 OpenCode 設定根目錄不能相同：$TARGET"
  fi
fi

# ---- 項目偵測 ---------------------------------------------------------------
SKILLS=()
for d in "$ROOT"/*/; do
  x="${d%/}"
  [ -f "$x/SKILL.md" ] || continue
  SKILLS+=("${x##*/}")
done

AGENTS=()
AGENT_FILES=()
if [ -d "$AGENT_SRC" ]; then
  for f in "$AGENT_SRC"/*.md; do
    [ -f "$f" ] || continue
    n="${f##*/}"
    AGENTS+=("${n%.md}")
    AGENT_FILES+=("$n")
  done
fi

BINS=()
if [ -d "$BIN_SRC" ]; then
  for f in "$BIN_SRC"/*.py; do
    [ -f "$f" ] || continue
    BINS+=("${f##*/}")
  done
fi

has_skill() {
  local n="$1" s
  [ ${#SKILLS[@]} -gt 0 ] || return 1
  for s in "${SKILLS[@]}"; do [ "$s" = "$n" ] && return 0; done
  return 1
}

has_agent() {
  local n="$1" a
  [ ${#AGENTS[@]} -gt 0 ] || return 1
  for a in "${AGENTS[@]}"; do [ "$a" = "$n" ] && return 0; done
  return 1
}

has_bin() {
  local n="$1" b
  [ ${#BINS[@]} -gt 0 ] || return 1
  for b in "${BINS[@]}"; do [ "$b" = "$n" ] && return 0; done
  return 1
}

in_wanted() {
  local n="$1" w
  [ ${#WANTED[@]} -gt 0 ] || return 1
  for w in "${WANTED[@]}"; do [ "$w" = "$n" ] && return 0; done
  return 1
}

# ---- 選取項目 ---------------------------------------------------------------
SELECTED_SKILLS=()
SELECTED_AGENTS=()
SELECTED_BINS=()
FULL_SKILLS=0
FULL_AGENTS=0

if [ ${#WANTED[@]} -gt 0 ]; then
  for w in "${WANTED[@]}"; do
    is_skill=0
    is_agent=0
    is_bin=0
    if has_skill "$w"; then is_skill=1; fi
    if has_agent "$w"; then is_agent=1; fi
    if has_bin "$w"; then is_bin=1; fi
    if [ $((is_skill + is_agent + is_bin)) -eq 0 ]; then
      die "不是可安裝的技能、agent 或輔助腳本：$w（技能：${SKILLS[*]:-無}；agents：${AGENTS[*]:-無}；腳本：${BINS[*]:-無}）"
    fi
    if [ "$is_skill" -eq 1 ] && [ "$is_agent" -eq 1 ]; then
      die "名稱同時對應技能與 agent，無法判定：$w"
    fi
    if [ "$is_skill" -eq 1 ] && [ "$SEL_SKILLS" -ne 1 ]; then
      die "目前只處理 OpenCode agents，不能選技能：$w"
    fi
    if [ "$is_agent" -eq 1 ] && [ "$SEL_AGENTS" -ne 1 ]; then
      die "目前只處理技能，不能選 agent：$w"
    fi
    if [ "$is_bin" -eq 1 ]; then
      if [ "$SEL_AGENTS" -ne 1 ]; then
        die "目前只處理技能，不能選輔助腳本：$w"
      fi
      if [ "$UNINSTALL" -ne 1 ]; then
        die "輔助腳本會隨 agent 一併安裝；安裝時請指定 agent 名稱，不要指定 $w"
      fi
    fi
  done

  if [ "$SEL_SKILLS" -eq 1 ] && [ ${#SKILLS[@]} -gt 0 ]; then
    for s in "${SKILLS[@]}"; do
      if in_wanted "$s"; then SELECTED_SKILLS+=("$s"); fi
    done
  fi

  if [ "$SEL_AGENTS" -eq 1 ]; then
    if [ ${#AGENTS[@]} -gt 0 ]; then
      for a in "${AGENTS[@]}"; do
        if in_wanted "$a"; then SELECTED_AGENTS+=("$a"); fi
      done
    fi
    if [ "$UNINSTALL" -ne 1 ] && [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
      if [ ${#BINS[@]} -gt 0 ]; then SELECTED_BINS=("${BINS[@]}"); fi
    elif [ ${#BINS[@]} -gt 0 ]; then
      for b in "${BINS[@]}"; do
        if in_wanted "$b"; then SELECTED_BINS+=("$b"); fi
      done
    fi
  fi
else
  if [ "$SEL_SKILLS" -eq 1 ]; then
    [ ${#SKILLS[@]} -gt 0 ] || die "根目錄下找不到任何含 SKILL.md 的技能目錄"
    FULL_SKILLS=1
    SELECTED_SKILLS=("${SKILLS[@]}")
  fi
  if [ "$SEL_AGENTS" -eq 1 ]; then
    [ ${#AGENTS[@]} -gt 0 ] || die "opencode/agents 下找不到任何 .md agent"
    FULL_AGENTS=1
    SELECTED_AGENTS=("${AGENTS[@]}")
    if [ ${#BINS[@]} -gt 0 ]; then SELECTED_BINS=("${BINS[@]}"); fi
  fi
fi

if [ ${#SELECTED_AGENTS[@]} -gt 0 ] && [ ${#BINS[@]} -eq 0 ]; then
  die "找到 OpenCode agent，但 opencode/bin 下沒有 .py 輔助腳本"
fi

# ---- 動作函式 ---------------------------------------------------------------
ensure_dir() { # $1=目錄 $2=說明
  local dir="$1" label="$2"
  [ -d "$dir" ] && return 0
  if [ -e "$dir" ]; then die "$label 不是目錄：$dir"; fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[預覽] 建立 %s %s\n' "$label" "$dir"
  else
    mkdir -p "$dir" || die "無法建立 $label：$dir"
  fi
}

backup_and_link() { # $1=標籤 $2=來源 $3=連結
  local label="$1" src="$2" link="$3" bak
  bak="$link.bak-$(date +%Y%m%d-%H%M%S)"
  while [ -e "$bak" ] || [ -L "$bak" ]; do bak="${bak}-x"; done
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[預覽] 備份 %s 後安裝（備份名：%s）\n' "$label" "${bak##*/}"
    backed=$((backed + 1))
    return 0
  fi
  if mv "$link" "$bak" && ln -s "$src" "$link"; then
    printf '[備份後安裝] %s（原項目 -> %s）\n' "$label" "${bak##*/}"
    backed=$((backed + 1))
  else
    printf '[失敗] 無法備份後安裝 %s\n' "$label" >&2
    failed=$((failed + 1))
  fi
}

install_item() { # $1=標籤 $2=來源 $3=連結 $4=所有權基底
  local label="$1" src="$2" link="$3" base="$4" cur
  if [ -L "$link" ]; then
    cur="$(link_target_abs "$link" || true)"
    if [ "$cur" = "$src" ]; then
      printf '[已最新] %s\n' "$label"
      unchanged=$((unchanged + 1))
      return 0
    fi
    if [ -n "$cur" ] && path_under "$cur" "$base"; then
      if [ "$DRY_RUN" -eq 1 ]; then
        printf '[預覽] 重指 %s -> %s\n' "$label" "$src"
        updated=$((updated + 1))
        return 0
      fi
      if rm -f "$link" && ln -s "$src" "$link"; then
        printf '[重指] %s -> %s\n' "$label" "$src"
        updated=$((updated + 1))
      else
        printf '[失敗] 無法重指 %s\n' "$label" >&2
        failed=$((failed + 1))
      fi
      return 0
    fi
    if [ "$FORCE" -ne 1 ]; then
      printf '[跳過] %s：目標已有非本倉庫的連結，未覆蓋（可加 --force 先備份再安裝）\n' "$label" >&2
      failed=$((failed + 1))
      return 0
    fi
    backup_and_link "$label" "$src" "$link"
    return 0
  fi
  if [ -e "$link" ]; then
    if [ "$FORCE" -ne 1 ]; then
      printf '[跳過] %s：目標已有實體項目，未覆蓋（可加 --force 先備份再安裝）\n' "$label" >&2
      failed=$((failed + 1))
      return 0
    fi
    backup_and_link "$label" "$src" "$link"
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[預覽] 新增 %s -> %s\n' "$label" "$src"
    created=$((created + 1))
    return 0
  fi
  if ln -s "$src" "$link"; then
    printf '[安裝] %s -> %s\n' "$label" "$src"
    created=$((created + 1))
  else
    printf '[失敗] 無法建立連結 %s\n' "$label" >&2
    failed=$((failed + 1))
  fi
}

prune_stale_in() { # $1=目錄 $2=所有權基底 $3...=保留的檔名
  local dir="$1" base="$2"
  shift 2
  local expected=("$@")
  local entry name cur keep e
  [ -d "$dir" ] || return 0
  for entry in "$dir"/*; do
    [ -L "$entry" ] || continue
    name="${entry##*/}"
    keep=0
    if [ ${#expected[@]} -gt 0 ]; then
      for e in "${expected[@]}"; do
        if [ "$e" = "$name" ]; then keep=1; break; fi
      done
    fi
    [ "$keep" -eq 1 ] && continue
    cur="$(link_target_abs "$entry" || true)"
    [ -n "$cur" ] || continue
    if ! path_under "$cur" "$base"; then continue; fi
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '[預覽] 清除陳舊連結 %s\n' "$name"
      pruned=$((pruned + 1))
      continue
    fi
    if rm -f "$entry"; then
      printf '[清除陳舊] %s\n' "$name"
      pruned=$((pruned + 1))
    else
      printf '[失敗] 無法清除陳舊連結 %s\n' "$name" >&2
      failed=$((failed + 1))
    fi
  done
}

remove_all_owned() { # $1=目錄 $2=所有權基底
  local dir="$1" base="$2" entry name cur
  [ -d "$dir" ] || return 0
  for entry in "$dir"/*; do
    [ -L "$entry" ] || continue
    cur="$(link_target_abs "$entry" || true)"
    [ -n "$cur" ] || continue
    if ! path_under "$cur" "$base"; then continue; fi
    name="${entry##*/}"
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '[預覽] 移除連結 %s\n' "$name"
      removed=$((removed + 1))
      continue
    fi
    if rm -f "$entry"; then
      printf '[移除] %s\n' "$name"
      removed=$((removed + 1))
    else
      printf '[失敗] 無法移除連結 %s\n' "$name" >&2
      failed=$((failed + 1))
    fi
  done
}

remove_named() { # $1=連結 $2=所有權基底 $3=標籤
  local link="$1" base="$2" label="$3" cur
  if [ -L "$link" ]; then
    cur="$(link_target_abs "$link" || true)"
    if [ -n "$cur" ] && path_under "$cur" "$base"; then
      if [ "$DRY_RUN" -eq 1 ]; then
        printf '[預覽] 移除連結 %s\n' "$label"
        removed=$((removed + 1))
        return 0
      fi
      if rm -f "$link"; then
        printf '[移除] %s\n' "$label"
        removed=$((removed + 1))
      else
        printf '[失敗] 無法移除連結 %s\n' "$label" >&2
        failed=$((failed + 1))
      fi
      return 0
    fi
    printf '[跳過] %s：不是本倉庫的連結，未移除\n' "$label" >&2
    return 0
  fi
  if [ -e "$link" ]; then
    printf '[跳過] %s：目標是實體項目，未移除\n' "$label" >&2
  fi
  return 0
}

count_owned_links() { # $1=目錄 $2=所有權基底
  local dir="$1" base="$2" entry cur count=0
  if [ ! -d "$dir" ]; then
    printf '0\n'
    return 0
  fi
  for entry in "$dir"/*; do
    [ -L "$entry" ] || continue
    cur="$(link_target_abs "$entry" || true)"
    [ -n "$cur" ] || continue
    if path_under "$cur" "$base"; then count=$((count + 1)); fi
  done
  printf '%s\n' "$count"
}

# ---- 主流程 -----------------------------------------------------------------
printf '[資訊] 本倉庫：%s\n' "$ROOT"
if [ "$SEL_SKILLS" -eq 1 ]; then
  printf '[資訊] 目標技能庫：%s\n' "$TARGET"
fi
if [ "$SEL_AGENTS" -eq 1 ]; then
  printf '[資訊] OpenCode 設定根目錄：%s\n' "$OPENCODE_DIR"
fi
if [ "$DRY_RUN" -eq 1 ]; then
  printf '[資訊] dry-run：只預覽，不做任何修改\n'
fi

if [ "$UNINSTALL" -eq 1 ]; then
  if [ "$SEL_SKILLS" -eq 1 ]; then
    if [ ${#WANTED[@]} -eq 0 ]; then
      remove_all_owned "$TARGET" "$ROOT"
    elif [ ${#SELECTED_SKILLS[@]} -gt 0 ]; then
      for s in "${SELECTED_SKILLS[@]}"; do
        remove_named "$TARGET/$s" "$ROOT" "技能 $s"
      done
    fi
  fi

  if [ "$SEL_AGENTS" -eq 1 ]; then
    if [ ${#WANTED[@]} -eq 0 ]; then
      remove_all_owned "$AGENTS_TARGET" "$AGENT_SRC"
      remove_all_owned "$BIN_TARGET" "$BIN_SRC"
    else
      removed_agent=0
      if [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
        for a in "${SELECTED_AGENTS[@]}"; do
          remove_named "$AGENTS_TARGET/$a.md" "$AGENT_SRC" "agent $a"
          removed_agent=1
        done
      fi
      if [ ${#SELECTED_BINS[@]} -gt 0 ]; then
        for b in "${SELECTED_BINS[@]}"; do
          remove_named "$BIN_TARGET/$b" "$BIN_SRC" "腳本 $b"
        done
      fi
      if [ "$removed_agent" -eq 1 ] && [ "$(count_owned_links "$AGENTS_TARGET" "$AGENT_SRC")" -eq 0 ]; then
        remove_all_owned "$BIN_TARGET" "$BIN_SRC"
      fi
    fi
  fi

  printf '完成：移除 %d、失敗 %d\n' "$removed" "$failed"
  [ "$failed" -eq 0 ] || exit 1
  exit 0
fi

if [ "$SEL_SKILLS" -eq 1 ] && [ ${#SELECTED_SKILLS[@]} -gt 0 ]; then
  ensure_dir "$TARGET" "目標技能庫"
fi
if [ "$SEL_AGENTS" -eq 1 ] && [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
  ensure_dir "$AGENTS_TARGET" "目標 agent 目錄"
  ensure_dir "$BIN_TARGET" "目標腳本目錄"
fi

if [ "$FULL_SKILLS" -eq 1 ]; then
  prune_stale_in "$TARGET" "$ROOT" "${SKILLS[@]}"
fi
if [ "$FULL_AGENTS" -eq 1 ]; then
  prune_stale_in "$AGENTS_TARGET" "$AGENT_SRC" "${AGENT_FILES[@]}"
  prune_stale_in "$BIN_TARGET" "$BIN_SRC" "${BINS[@]}"
fi

if [ ${#SELECTED_SKILLS[@]} -gt 0 ]; then
  for s in "${SELECTED_SKILLS[@]}"; do
    install_item "技能 $s" "$ROOT/$s" "$TARGET/$s" "$ROOT"
  done
fi
if [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
  for a in "${SELECTED_AGENTS[@]}"; do
    install_item "agent $a" "$AGENT_SRC/$a.md" "$AGENTS_TARGET/$a.md" "$AGENT_SRC"
  done
fi
if [ ${#SELECTED_BINS[@]} -gt 0 ]; then
  for b in "${SELECTED_BINS[@]}"; do
    install_item "腳本 $b" "$BIN_SRC/$b" "$BIN_TARGET/$b" "$BIN_SRC"
  done
fi

printf '完成：新增 %d、重指 %d、已最新 %d、備份 %d、清除陳舊 %d、失敗 %d\n' \
  "$created" "$updated" "$unchanged" "$backed" "$pruned" "$failed"

if [ "$DRY_RUN" -ne 1 ] && [ $((created + updated + backed)) -gt 0 ]; then
  printf '提示：連結即時生效；若 OpenCode 有技能或 agent 清單快取，重新載入即可看到。\n'
fi

[ "$failed" -eq 0 ] || exit 1
