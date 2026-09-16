#!/usr/bin/env bash
# 將 Word 文件（.docx / 舊版 .doc）轉成 markdown，抽出圖片為媒體資產。
# 用法: doc-to-md.sh <來源文件> [輸出資料夾]
set -euo pipefail

src="$1"
[ -f "$src" ] || { echo "找不到來源文件: $src" >&2; exit 1; }
src="$(readlink -f -- "$src")"
name="$(basename -- "$src")"
stem="${name%.*}"
ext="${name##*.}"
srcdir="$(dirname -- "$src")"

command -v pandoc >/dev/null || { echo "需要 pandoc（3.x）" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

case "$ext" in
  docx) ;;
  doc)
    command -v soffice >/dev/null || { echo "舊版 .doc 需要 LibreOffice（soffice）做相容性橋接" >&2; exit 1; }
    soffice -env:UserInstallation="file://$work/lo" --headless \
      --convert-to "docx:MS Word 2007 XML" --outdir "$work" "$src" >/dev/null
    [ -f "$work/$stem.docx" ] || { echo "LibreOffice 轉檔失敗: $src" >&2; exit 1; }
    src="$work/$stem.docx"
    ;;
  *) echo "只支援 .docx / .doc，收到: .$ext" >&2; exit 1;;
esac

outdir="${2:-$srcdir/$stem}"
outdir="${outdir%/}"
mkdir -p "$outdir/assets"

# 在輸出資料夾內執行，pandoc 才會寫出相對路徑；只留 pipe table
( cd "$outdir" && pandoc "$src" -o "$stem.md" \
  -t markdown-raw_html-simple_tables-multiline_tables-grid_tables \
  --wrap=none --markdown-headings=atx \
  --extract-media=assets )

# 後製：搬平 media/、語意化改名、改寫引用、補空 alt
n=0
shopt -s nullglob
for f in "$outdir"/assets/media/*; do
  n=$((n + 1))
  oldref="assets/media/$(basename -- "$f")"
  new="${stem}-image-${n}.${f##*.}"
  newref="assets/$new"
  mv -- "$f" "$outdir/assets/$new"
  sed -i \
    -e "s|$oldref|$newref|g" \
    -e "s|!\[\]($newref)|![${stem}-image-${n}]($newref)|g" \
    "$outdir/$stem.md"
done
shopt -u nullglob
rmdir "$outdir/assets/media" 2>/dev/null || true
rmdir "$outdir/assets" 2>/dev/null || true

# 去除寬高屬性尾巴
sed -i -E 's|\{width="[^"]*"( height="[^"]*")?\}||g' "$outdir/$stem.md"

echo "$outdir/$stem.md（媒體資產 ${n} 張）"
