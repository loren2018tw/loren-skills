#!/usr/bin/env bash
# install.sh 生命週期 smoke：技能＋OpenCode agents／bin → 冪等 → 外來項目不動
# → 名稱選取 → 清除陳舊 → 卸載 → 目標乾淨。
# 可本機執行（Linux/macOS）；CI 亦會呼叫。
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
BASE="$(mktemp -d "${TMPDIR:-/tmp}/loren-skills-smoke.XXXXXX")"
TARGET="$BASE/skills"
OPENCODE="$BASE/opencode"
OUTSIDE="$BASE/outside"
trap 'rm -rf -- "$BASE"' EXIT

fail=0
ok()  { printf '[OK]   %s\n' "$1"; }
bad() { printf '[FAIL] %s\n' "$1" >&2; fail=1; }

check_link() { # $1=連結 $2=預期目標 $3=標籤
  if [ -L "$1" ] && [ "$(readlink "$1")" = "$2" ]; then
    ok "$3 連結指向正確"
  else
    bad "$3 未建立連結或指向錯誤"
  fi
}

check_no_link() { # $1=連結 $2=標籤
  if [ -L "$1" ]; then bad "$2 仍存在"; else ok "$2 已移除"; fi
}

count_links() {
  find "$1" -maxdepth 2 -type l 2>/dev/null | wc -l
}

# ---- 測試素材 ---------------------------------------------------------------
skills=()
for d in "$ROOT"/*/; do
  [ -f "${d}SKILL.md" ] && skills+=("${d%/}")
done
if [ "${#skills[@]}" -eq 0 ]; then bad "找不到技能"; exit 1; fi
ok "偵測到 ${#skills[@]} 個技能"

agents=()
for f in "$ROOT"/opencode/agents/*.md; do
  [ -f "$f" ] && agents+=("$f")
done
if [ "${#agents[@]}" -eq 0 ]; then bad "找不到 OpenCode agents"; exit 1; fi
ok "偵測到 ${#agents[@]} 個 OpenCode agent"

bins=()
for f in "$ROOT"/opencode/bin/*.py; do
  [ -f "$f" ] && bins+=("$f")
done
if [ "${#bins[@]}" -eq 0 ]; then bad "找不到輔助腳本"; exit 1; fi
ok "偵測到 ${#bins[@]} 個輔助腳本"

mkdir -p "$TARGET/foreign-copy" "$OPENCODE/agents" "$OPENCODE/bin" "$OUTSIDE"
printf 'outside\n' > "$OUTSIDE/keep.txt"
printf 'remote\n' > "$OPENCODE/agents/remote.md"
ln -s "$OUTSIDE" "$TARGET/foreign-link"
ln -s "$OUTSIDE/keep.txt" "$OPENCODE/agents/foreign-link.md"
ln -s "$OUTSIDE/keep.txt" "$OPENCODE/bin/foreign-link.py"

# ---- 1) 全量安裝 ------------------------------------------------------------
"$ROOT/install.sh" --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
for s in "${skills[@]}"; do
  name="${s##*/}"
  check_link "$TARGET/$name" "$s" "技能 $name"
done
for f in "${agents[@]}"; do
  name="${f##*/}"
  check_link "$OPENCODE/agents/$name" "$f" "agent $name"
done
for f in "${bins[@]}"; do
  name="${f##*/}"
  check_link "$OPENCODE/bin/$name" "$f" "腳本 $name"
done

if [ "$(cat "$OPENCODE/agents/remote.md")" = "remote" ]; then
  ok "既有實體 agent（remote.md）未被動到"
else
  bad "既有實體 agent 被動到"
fi
check_link "$OPENCODE/agents/foreign-link.md" "$OUTSIDE/keep.txt" "agents 外來連結"
check_link "$OPENCODE/bin/foreign-link.py" "$OUTSIDE/keep.txt" "bin 外來連結"
if [ -d "$TARGET/foreign-copy" ] && [ -L "$TARGET/foreign-link" ]; then
  ok "技能目標的外來項目未被動到"
else
  bad "技能目標的外來項目被動到"
fi

# ---- 2) 冪等 ----------------------------------------------------------------
out2="$("$ROOT/install.sh" --target "$TARGET" --opencode-dir "$OPENCODE")"
case "$out2" in
  *"新增 0"*) ok "第二次安裝冪等（新增 0）" ;;
  *) bad "第二次安裝非冪等" ;;
esac
case "$out2" in
  *"已最新"*) ok "第二次安裝回報已最新" ;;
  *) bad "第二次安裝未回報已最新" ;;
esac

# ---- 3) 清除陳舊連結 --------------------------------------------------------
ln -s "$ROOT/opencode/agents/gone.md" "$OPENCODE/agents/gone.md"
ln -s "$ROOT/opencode/bin/gone.py" "$OPENCODE/bin/gone.py"
"$ROOT/install.sh" --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
check_no_link "$OPENCODE/agents/gone.md" "陳舊 agent 連結"
check_no_link "$OPENCODE/bin/gone.py" "陳舊腳本連結"
check_link "$OPENCODE/agents/foreign-link.md" "$OUTSIDE/keep.txt" "清除陳舊後的 agents 外來連結"

# ---- 4) 名稱卸載：最後一個 agent 移除時一併清 bin -------------------------
"$ROOT/install.sh" --uninstall geminiimage --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
check_no_link "$OPENCODE/agents/geminiimage.md" "agent geminiimage"
check_link "$OPENCODE/agents/gptimage.md" "$ROOT/opencode/agents/gptimage.md" "agent gptimage 仍在"
check_link "$OPENCODE/bin/geminiimage.py" "$ROOT/opencode/bin/geminiimage.py" "還有 agent 時保留腳本"

"$ROOT/install.sh" --uninstall gptimage --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
check_no_link "$OPENCODE/agents/gptimage.md" "agent gptimage"
check_no_link "$OPENCODE/bin/geminiimage.py" "沒有 agent 時移除腳本"
check_no_link "$OPENCODE/bin/gptimage.py" "沒有 agent 時移除腳本"

# ---- 5) 類別卸載：--agents 不動技能；--skills 只動技能 -------------------
"$ROOT/install.sh" --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
"$ROOT/install.sh" --uninstall --agents --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
check_no_link "$OPENCODE/agents/geminiimage.md" "卸載 agents 後的 agent"
check_no_link "$OPENCODE/bin/geminiimage.py" "卸載 agents 後的腳本"
check_link "$TARGET/who-is-loren" "$ROOT/who-is-loren" "卸載 agents 後技能仍在"

"$ROOT/install.sh" --uninstall --skills --target "$TARGET" --opencode-dir "$OPENCODE" >/dev/null
check_no_link "$TARGET/who-is-loren" "卸載技能後的技能"
check_link "$OPENCODE/agents/foreign-link.md" "$OUTSIDE/keep.txt" "全數卸載後 agents 外來連結仍在"
check_link "$OPENCODE/bin/foreign-link.py" "$OUTSIDE/keep.txt" "全數卸載後 bin 外來連結仍在"
if [ "$(cat "$OPENCODE/agents/remote.md")" = "remote" ]; then ok "全數卸載後實體 agent 仍在"; else bad "全數卸載後實體 agent 消失"; fi

n_links=$(count_links "$OPENCODE")
if [ "$n_links" -eq 2 ]; then ok "卸載後 OpenCode 目標僅剩 2 個外來連結"; else bad "卸載後 OpenCode 連結數為 $n_links（預期 2）"; fi
n_links=$(count_links "$TARGET")
if [ "$n_links" -eq 1 ]; then ok "卸載後技能目標僅剩外來連結"; else bad "卸載後技能連結數為 $n_links（預期 1）"; fi

# ---- 6) 只安裝技能：不建立 OpenCode 目錄 ---------------------------------
T2="$BASE/skills-only"
O2="$BASE/opencode-skills-only"
"$ROOT/install.sh" --skills --target "$T2" --opencode-dir "$O2" >/dev/null
check_link "$T2/who-is-loren" "$ROOT/who-is-loren" "只安裝技能"
if [ -e "$O2" ]; then bad "只安裝技能卻建立了 OpenCode 目錄"; else ok "只安裝技能未建立 OpenCode 目錄"; fi
"$ROOT/install.sh" --uninstall --skills --target "$T2" --opencode-dir "$O2" >/dev/null

# ---- 7) 只安裝 agents：不建立技能目錄；指定名稱只裝該 agent -------------
T3="$BASE/skills-agents-only"
O3="$BASE/opencode-agents-only"
"$ROOT/install.sh" --agents --target "$T3" --opencode-dir "$O3" >/dev/null
check_link "$O3/agents/geminiimage.md" "$ROOT/opencode/agents/geminiimage.md" "只安裝 agents"
check_link "$O3/bin/geminiimage.py" "$ROOT/opencode/bin/geminiimage.py" "只安裝 agents 的腳本"
if [ -e "$T3" ]; then bad "只安裝 agents 卻建立了技能目錄"; else ok "只安裝 agents 未建立技能目錄"; fi
"$ROOT/install.sh" --uninstall --agents --target "$T3" --opencode-dir "$O3" >/dev/null

T4="$BASE/skills-named-agent"
O4="$BASE/opencode-named-agent"
"$ROOT/install.sh" geminiimage --target "$T4" --opencode-dir "$O4" >/dev/null
check_link "$O4/agents/geminiimage.md" "$ROOT/opencode/agents/geminiimage.md" "指定名稱安裝 agent"
check_no_link "$O4/agents/gptimage.md" "未指定的 agent"
check_link "$O4/bin/geminiimage.py" "$ROOT/opencode/bin/geminiimage.py" "指定 agent 的腳本"
check_link "$O4/bin/gptimage.py" "$ROOT/opencode/bin/gptimage.py" "指定 agent 仍安裝共用腳本集"
if [ -e "$T4" ]; then bad "指定 agent 卻建立了技能目錄"; else ok "指定 agent 未建立技能目錄"; fi
"$ROOT/install.sh" --uninstall --agents --target "$T4" --opencode-dir "$O4" >/dev/null

# ---- 8) dry-run：只預覽，不建立任何目錄 ----------------------------------
T5="$BASE/skills-dry"
O5="$BASE/opencode-dry"
out5="$("$ROOT/install.sh" --dry-run --target "$T5" --opencode-dir "$O5")"
case "$out5" in
  *"[預覽]"*) ok "dry-run 有預覽輸出" ;;
  *) bad "dry-run 沒有預覽輸出" ;;
esac
if [ -e "$T5" ] || [ -e "$O5" ]; then bad "dry-run 建立了目錄"; else ok "dry-run 未建立任何目錄"; fi

# ---- 9) 外來同名連結：無 --force 跳過；--force 備份後連結 ----------------
T6="$BASE/skills-conflict"
O6="$BASE/opencode-conflict"
mkdir -p "$O6/agents" "$O6/bin"
printf 'foreign-agent\n' > "$OUTSIDE/foreign-agent.md"
ln -s "$OUTSIDE/foreign-agent.md" "$O6/agents/geminiimage.md"
if "$ROOT/install.sh" geminiimage --target "$T6" --opencode-dir "$O6" >/dev/null 2>&1; then
  bad "外來同名連結未被擋下"
else
  ok "外來同名連結被擋下"
fi
check_link "$O6/agents/geminiimage.md" "$OUTSIDE/foreign-agent.md" "外來同名連結"

"$ROOT/install.sh" geminiimage --force --target "$T6" --opencode-dir "$O6" >/dev/null
check_link "$O6/agents/geminiimage.md" "$ROOT/opencode/agents/geminiimage.md" "--force 後 agent 連結"
bak="$(find "$O6/agents" -maxdepth 1 -name 'geminiimage.md.bak-*' | head -1)"
if [ -n "$bak" ] && [ -L "$bak" ] && [ "$(readlink "$bak")" = "$OUTSIDE/foreign-agent.md" ]; then
  ok "--force 備份了原外來連結"
else
  bad "--force 未正確備份原外來連結"
fi
"$ROOT/install.sh" --uninstall --agents --target "$T6" --opencode-dir "$O6" >/dev/null

if [ "$fail" -eq 0 ]; then printf 'Unix smoke 全部通過\n'; else printf 'Unix smoke 失敗\n' >&2; exit 1; fi
