#!/usr/bin/env bash
# 將 Word 文件（.docx / 舊版 .doc）轉成 markdown，抽出圖片為媒體資產。
# 管線: [soffice 橋接] → markitdown 全文（圖=佔位符）→ merge_md_images.py 還原圖檔
# 用法: doc-to-md.sh <來源文件> [輸出資料夾]
set -euo pipefail

src="$1"
[ -f "$src" ] || { echo "找不到來源文件: $src" >&2; exit 1; }
src="$(readlink -f -- "$src")"
name="$(basename -- "$src")"
stem="${name%.*}"
ext="${name##*.}"
srcdir="$(dirname -- "$src")"

command -v soffice >/dev/null || { echo "需要 LibreOffice（soffice）" >&2; exit 1; }
command -v markitdown >/dev/null || { echo "需要 markitdown（uv tool install markitdown）" >&2; exit 1; }
command -v python3 >/dev/null || { echo "需要 python3" >&2; exit 1; }
scriptdir="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

case "$ext" in
  docx) ;;
  doc)
    soffice -env:UserInstallation="file://$work/lo" --headless \
      --convert-to "docx:MS Word 2007 XML" --outdir "$work" "$src" >/dev/null
    [ -f "$work/$stem.docx" ] || { echo "LibreOffice 轉檔失敗: $src" >&2; exit 1; }
    docx="$work/$stem.docx"
    ;;
  *) echo "只支援 .docx / .doc，收到: .$ext" >&2; exit 1;;
esac
[ -n "${docx:-}" ] || docx="$src"

outdir="${2:-$srcdir/$stem}"
outdir="${outdir%/}"
mkdir -p "$outdir"

# 1) markitdown：全文轉 md，圖片變 data URI 佔位符
markitdown "$docx" -o "$work/markitdown.md" 2>"$work/markitdown.err" || {
  echo "markitdown 轉換失敗:" >&2; cat "$work/markitdown.err" >&2; exit 1; }

# 2) 合併：依 docx 圖片引用順序還原 assets/<stem>-image-K.ext
python3 "$scriptdir/merge_md_images.py" "$docx" "$work/markitdown.md" "$outdir"

echo "$outdir/$stem.md"
