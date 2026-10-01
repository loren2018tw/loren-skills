#!/usr/bin/env bash
# 編碼與行尾不變式的自動檢查。可本機執行；CI 亦會呼叫（見 .github/workflows/checks.yml）。
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

fail=0
ok()  { printf '[OK]   %s\n' "$1"; }
bad() { printf '[FAIL] %s\n' "$1" >&2; fail=1; }
bom() { head -c 3 "$1" | od -An -tx1 | tr -d ' \n'; }
list() { git ls-files --cached --others --exclude-standard -z -- "$@" | tr '\000' '\n'; }

# ---- *.ps1：UTF-8 BOM ----
while IFS= read -r f; do
  if [ "$(bom "$f")" = "efbbbf" ]; then ok "$f 具 UTF-8 BOM"; else bad "$f 缺 UTF-8 BOM"; fi
done < <(list '*.ps1')

# ---- install.ps1：要求 PowerShell 7.2 ----
if grep -q '#Requires -Version 7\.2' install.ps1; then
  ok "install.ps1 要求 PowerShell 7.2"
else
  bad "install.ps1 缺少 '#Requires -Version 7.2'"
fi

# ---- *.cmd / *.bat：純 ASCII、無 BOM ----
while IFS= read -r f; do
  if [ -n "$(LC_ALL=C tr -d '\000-\177' < "$f")" ]; then
    bad "$f 含非 ASCII 位元組"
  else
    ok "$f 為純 ASCII"
  fi
  if [ "$(bom "$f")" = "efbbbf" ]; then bad "$f 帶了 BOM"; else ok "$f 無 BOM"; fi
done < <(list '*.cmd' '*.bat')

# ---- *.sh / *.py / *.md：LF ----
crlf_files=""
while IFS= read -r f; do
  if grep -q $'\r' "$f"; then crlf_files="$crlf_files $f"; fi
done < <(list '*.sh' '*.py' '*.md')
if [ -n "$crlf_files" ]; then bad "以下檔案含 CRLF：$crlf_files"; else ok "*.sh / *.py / *.md 皆為 LF"; fi

# ---- 行尾屬性 ----
while IFS= read -r f; do
  got="$(git check-attr eol -- "$f" | awk -F': ' '{print $3}')"
  if [ "$got" = "crlf" ]; then ok "$f eol=crlf"; else bad "$f eol=$got（預期 crlf）"; fi
done < <(list '*.ps1' '*.cmd' '*.bat')

if [ "$fail" -eq 0 ]; then printf '編碼檢查全部通過\n'; else printf '編碼檢查失敗\n' >&2; exit 1; fi
