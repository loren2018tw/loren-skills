#!/usr/bin/env bash
# install.sh 生命週期 smoke：安裝 → 冪等 → 外來項目不動 → 卸載 → 目標乾淨。
# 可本機執行（Linux/macOS）；CI 亦會呼叫。
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TARGET="$(mktemp -d "${TMPDIR:-/tmp}/loren-skills-smoke.XXXXXX")"
OUTSIDE="$(mktemp -d "${TMPDIR:-/tmp}/loren-skills-outside.XXXXXX")"
trap 'rm -rf -- "$TARGET" "$OUTSIDE"' EXIT

fail=0
ok()  { printf '[OK]   %s\n' "$1"; }
bad() { printf '[FAIL] %s\n' "$1" >&2; fail=1; }

# 技能清單
skills=()
for d in "$ROOT"/*/; do
  [ -f "${d}SKILL.md" ] && skills+=("${d%/}")
done
if [ "${#skills[@]}" -eq 0 ]; then bad "找不到技能"; exit 1; fi
ok "偵測到 ${#skills[@]} 個技能"

# 外來項目：實體目錄複本＋指向倉庫外的連結
mkdir -p "$TARGET/foreign-copy"
ln -s "$OUTSIDE" "$TARGET/foreign-link"

# 1) 安裝
"$ROOT/install.sh" --target "$TARGET" >/dev/null
for s in "${skills[@]}"; do
  name="${s##*/}"
  link="$TARGET/$name"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "$s" ]; then
    ok "$name 連結指向正確"
  else
    bad "$name 未建立連結或指向錯誤"
  fi
done

# 2) 冪等
out2="$("$ROOT/install.sh" --target "$TARGET")"
case "$out2" in
  *"新增 0"*) ok "第二次安裝冪等（新增 0）" ;;
  *) bad "第二次安裝非冪等" ;;
esac
case "$out2" in
  *"已最新"*) ok "第二次安裝回報已最新" ;;
  *) bad "第二次安裝未回報已最新" ;;
esac

# 3) 卸載：本倉庫連結全移除、外來項目完好
"$ROOT/install.sh" --uninstall --target "$TARGET" >/dev/null
for s in "${skills[@]}"; do
  name="${s##*/}"
  if [ -e "$TARGET/$name" ] || [ -L "$TARGET/$name" ]; then
    bad "$name 卸載後仍存在"
  else
    ok "$name 已移除"
  fi
done
if [ -d "$TARGET/foreign-copy" ]; then ok "外來複本未被動到"; else bad "外來複本被刪"; fi
if [ -L "$TARGET/foreign-link" ]; then ok "外來連結未被動到"; else bad "外來連結被刪"; fi
n_links=$(find "$TARGET" -maxdepth 1 -type l | wc -l)
if [ "$n_links" -eq 1 ]; then ok "卸載後目標僅剩外來連結"; else bad "卸載後連結數為 $n_links（預期 1）"; fi

if [ "$fail" -eq 0 ]; then printf 'Unix smoke 全部通過\n'; else printf 'Unix smoke 失敗\n' >&2; exit 1; fi
