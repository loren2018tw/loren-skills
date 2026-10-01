#!/usr/bin/env bash
#
# 將本倉庫的技能目錄以符號連結安裝到目標技能庫（預設 ~/.agents/skills）。
# 連結安裝＝本倉庫更新即時反映；--uninstall 可完整還原。
#
# 用法: ./install.sh [--target DIR] [--uninstall] [--dry-run] [--force] [技能名...]

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

TARGET=""
UNINSTALL=0
DRY_RUN=0
FORCE=0
WANTED=()

created=0 updated=0 unchanged=0 backed=0 pruned=0 removed=0 failed=0

die() { printf '[錯誤] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
用法: ./install.sh [選項] [技能名...]

將本倉庫根目錄下含 SKILL.md 的技能目錄，以符號連結安裝到目標技能庫。
之後在本倉庫 git pull，agent 端即時生效，無需重裝。

選項:
  --target DIR   安裝位置（預設 ~/.agents/skills）
  --uninstall    移除目標技能庫中指向本倉庫的連結（可搭配技能名只移除部分）
  --dry-run      只預覽動作，不做任何修改
  --force        目標已有同名實體項目時，先備份成 <名稱>.bak-<時間戳> 再建立連結
  -h, --help     顯示本說明

不帶技能名＝全量安裝（並清除陳舊連結）；指定技能名＝只處理這些技能。

範例:
  ./install.sh                        # 全量安裝
  ./install.sh who-is-loren           # 只安裝一個技能
  ./install.sh --dry-run              # 預覽全量安裝
  ./install.sh --uninstall            # 全部卸載
  ./install.sh --target /tmp/skills   # 安裝到指定位置（測試用）
EOF
}

# ---- 平台檢查 ---------------------------------------------------------------
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    die "偵測到 Git Bash／MSYS／Cygwin：ln -s 在這些環境不是真正的連結，請改用 Windows PowerShell 執行 install.ps1。"
    ;;
esac

# ---- 解析參數 ---------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      [ $# -ge 2 ] || die "--target 需要一個目錄參數"
      TARGET="$2"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
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

if [ -z "$TARGET" ]; then
  [ -n "${HOME:-}" ] || die "找不到 HOME，請用 --target 指定安裝位置"
  TARGET="$HOME/.agents/skills"
fi
case "$TARGET" in
  /*) : ;;
  *) TARGET="$PWD/$TARGET" ;;
esac
TARGET="${TARGET%/}"
[ -n "$TARGET" ] || die "目標技能庫路徑不合法"
case "$TARGET" in
  "$ROOT"|"$ROOT"/*) die "目標技能庫不能位於本倉庫內：$TARGET" ;;
esac
if [ -e "$TARGET" ] && [ ! -d "$TARGET" ]; then
  die "目標技能庫不是目錄：$TARGET"
fi

# ---- 技能偵測 ---------------------------------------------------------------
SKILLS=()
for d in "$ROOT"/*/; do
  x="${d%/}"
  [ -f "$x/SKILL.md" ] || continue
  SKILLS+=("${x##*/}")
done
[ ${#SKILLS[@]} -gt 0 ] || die "根目錄下找不到任何含 SKILL.md 的技能目錄"

has_skill() {
  local n="$1" s
  for s in "${SKILLS[@]}"; do [ "$s" = "$n" ] && return 0; done
  return 1
}

in_wanted() {
  local n="$1" w
  for w in "${WANTED[@]}"; do [ "$w" = "$n" ] && return 0; done
  return 1
}

repo_link_target() { # $1=路徑；若為指向本倉庫的連結，印出其目標
  local link
  link="$(readlink "$1" 2>/dev/null)" || return 1
  case "$link" in
    /*) : ;;
    *) link="$(cd -- "$(dirname -- "$1")" && pwd -P)/${link#./}" ;;
  esac
  case "$link" in
    "$ROOT"/*) printf '%s\n' "$link"; return 0 ;;
  esac
  return 1
}

# ---- 動作函式 ---------------------------------------------------------------
install_one() {
  local name="$1" src="$ROOT/$1" link="$TARGET/$1" cur bak
  if [ -L "$link" ]; then
    cur="$(readlink "$link" 2>/dev/null || true)"
    if [ "$cur" = "$src" ]; then
      printf '[已最新] %s\n' "$name"
      unchanged=$((unchanged + 1))
      return 0
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '[預覽] 重指 %s -> %s\n' "$name" "$src"
      updated=$((updated + 1))
      return 0
    fi
    if rm -f "$link" && ln -s "$src" "$link"; then
      printf '[重指] %s -> %s\n' "$name" "$src"
      updated=$((updated + 1))
    else
      printf '[失敗] 無法重指 %s\n' "$name" >&2
      failed=$((failed + 1))
    fi
    return 0
  fi
  if [ -e "$link" ]; then
    if [ "$FORCE" -ne 1 ]; then
      printf '[跳過] %s：目標已有實體項目，未覆蓋（可加 --force 先備份再安裝）\n' "$name" >&2
      failed=$((failed + 1))
      return 0
    fi
    bak="$link.bak-$(date +%Y%m%d-%H%M%S)"
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '[預覽] 備份 %s 後安裝（備份名：%s）\n' "$name" "${bak##*/}"
      backed=$((backed + 1))
      return 0
    fi
    if mv "$link" "$bak" && ln -s "$src" "$link"; then
      printf '[備份後安裝] %s（原項目 -> %s）\n' "$name" "${bak##*/}"
      backed=$((backed + 1))
    else
      printf '[失敗] 無法備份後安裝 %s\n' "$name" >&2
      failed=$((failed + 1))
    fi
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[預覽] 新增 %s -> %s\n' "$name" "$src"
    created=$((created + 1))
    return 0
  fi
  if ln -s "$src" "$link"; then
    printf '[安裝] %s -> %s\n' "$name" "$src"
    created=$((created + 1))
  else
    printf '[失敗] 無法建立連結 %s\n' "$name" >&2
    failed=$((failed + 1))
  fi
}

prune_stale() {
  local entry name
  [ -d "$TARGET" ] || return 0
  for entry in "$TARGET"/*; do
    [ -L "$entry" ] || continue
    name="${entry##*/}"
    has_skill "$name" && continue
    repo_link_target "$entry" >/dev/null || continue
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

uninstall_links() {
  local entry name
  [ -d "$TARGET" ] || return 0
  for entry in "$TARGET"/*; do
    [ -L "$entry" ] || continue
    name="${entry##*/}"
    if [ ${#WANTED[@]} -gt 0 ]; then
      in_wanted "$name" || continue
    fi
    repo_link_target "$entry" >/dev/null || continue
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

# ---- 主流程 -----------------------------------------------------------------
printf '[資訊] 本倉庫：%s\n' "$ROOT"
printf '[資訊] 目標技能庫：%s\n' "$TARGET"
if [ "$DRY_RUN" -eq 1 ]; then
  printf '[資訊] dry-run：只預覽，不做任何修改\n'
fi

if [ "$UNINSTALL" -eq 1 ]; then
  uninstall_links
  printf '完成：移除 %d、失敗 %d\n' "$removed" "$failed"
  [ "$failed" -eq 0 ] || exit 1
  exit 0
fi

if [ ${#WANTED[@]} -gt 0 ]; then
  for w in "${WANTED[@]}"; do
    has_skill "$w" || die "不是可安裝的技能：$w（可安裝：${SKILLS[*]}）"
  done
fi

if [ ! -d "$TARGET" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[預覽] 建立目標技能庫 %s\n' "$TARGET"
  else
    mkdir -p "$TARGET" || die "無法建立目標技能庫：$TARGET"
  fi
fi

if [ ${#WANTED[@]} -eq 0 ]; then
  prune_stale
fi

SELECTED=()
if [ ${#WANTED[@]} -eq 0 ]; then
  SELECTED=("${SKILLS[@]}")
else
  for s in "${SKILLS[@]}"; do
    if in_wanted "$s"; then SELECTED+=("$s"); fi
  done
fi

for s in "${SELECTED[@]}"; do
  install_one "$s"
done

printf '完成：新增 %d、重指 %d、已最新 %d、備份 %d、清除陳舊 %d、失敗 %d\n' \
  "$created" "$updated" "$unchanged" "$backed" "$pruned" "$failed"

if [ "$DRY_RUN" -ne 1 ] && [ $((created + updated + backed)) -gt 0 ]; then
  printf '提示：連結即時生效；若 agent 端有技能清單快取，重開 session 即可看到。\n'
fi

[ "$failed" -eq 0 ] || exit 1
