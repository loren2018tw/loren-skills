#!/usr/bin/env python3
"""把 markitdown 輸出的 md 中圖片佔位符，還原成 docx 內的真實圖檔。

用法: merge_md_images.py <docx> <markitdown.md> <輸出目錄>

原理:
  markitdown（mammoth）轉 docx 時，圖片變成截斷的 data URI 佔位符
  `![alt](data:image/jpeg;base64...)`（alt 可能為空，也可能帶 docx 內部
  圖片名，隨 markitdown 版本而異），且佔位符數量與 docx 內圖片引用數一致、
  順序同 body 順序。本腳本依 docx `word/document.xml` 中 mc:Choice 分支的
  r:embed/r:id 引用順序（跳過 mc:Fallback 避免重複），把第 k 個佔位符
  換成第 k 張圖：`![<stem>-image-k](assets/<stem>-image-k.<ext>)`。

  群組示意圖（wpg:wgp：一張底圖＋多個帶座標文字方塊）的圖內文字另由
  annotate_images 繪回底圖（覆蓋原檔、一律存 PNG，md 引用同步改副檔名），
  讓讀者能把文字對回圖上位置；圖下文字不動，仍是 agent 的可靠來源。

  `.emf/.wmf` 向量圖另以 soffice 轉高解析 png（原檔保留在 assets 備查），
  md 引用指向 png；轉換失敗時引用維持原格式。

  docx 解析見 _docx.py；標注需 Pillow（本 skill 必要依賴，見
  docs/adr/0005-doc2md-pillow-annotated-images.md），缺 Pillow 即失敗。

驗證:
  佔位符數 ≠ 引用數時仍完成對位（多出的佔位符保留原樣），
  但以 exit 2 + 警告回報，交由上層驗收攔截。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import annotate_images  # noqa: E402
from _compat import find_tool, use_utf8_stdio  # noqa: E402
from _docx import group_text_boxes, image_refs  # noqa: E402

PNG_FILTER = ('png:draw_png_Export:{"PixelWidth":{"type":"long","value":1600},'
              '"PixelHeight":{"type":"long","value":2200}}')


def convert_metafiles_to_png(assets: str, work: str) -> dict:
    """把 assets 內的 .emf/.wmf 以 soffice 轉成高解析 png（保留原檔）。

    回傳 {原檔名: png檔名}；轉換失敗者不在 dict 中（引用維持原格式）。
    """
    targets = sorted(f for f in os.listdir(assets)
                     if f.lower().endswith(('.emf', '.wmf')))
    if not targets:
        return {}

    soffice = find_tool('soffice')
    if soffice is None:
        print('警告: 找不到 soffice，無法將 emf/wmf 轉 png，引用保留原格式',
              file=sys.stderr)
        return {}

    renamed = {}
    for f in targets:
        src = os.path.join(assets, f)
        r = subprocess.run(
            [soffice, f'-env:UserInstallation={(Path(work) / "lo").as_uri()}',
             '--headless', '--convert-to', PNG_FILTER,
             '--outdir', assets, src],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120)
        png = os.path.splitext(src)[0] + '.png'
        if r.returncode == 0 and os.path.exists(png):
            # <stem>-image-K.emf → <stem>-image-K.png；emf/wmf 原檔留著備查
            renamed[f] = os.path.basename(png)
        else:
            print(f'警告: emf/wmf 轉 png 失敗: {f}（引用保留原檔）', file=sys.stderr)
    return renamed


def main() -> int:
    use_utf8_stdio()
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 1
    docx, md_src, outdir = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/\\')
    stem = os.path.splitext(os.path.basename(docx))[0]
    if not annotate_images.available():
        print('需要 Pillow（群組示意圖文字標注）: python3 -m pip install pillow'
              '（Windows: py -3 -m pip install pillow）', file=sys.stderr)
        return 1
    assets = os.path.join(outdir, 'assets')
    os.makedirs(assets, exist_ok=True)

    # ---- 1. docx: body 順序的圖片引用（只掃 mc:Choice，跳過 mc:Fallback）----
    with zipfile.ZipFile(docx) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
        rmap = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(media/[^"]+)"', rels))
        refs = image_refs(xml, rmap)

        # ---- 2a. 抽出 media 至 assets/，並依引用順序改名 ----
        media_files = sorted(set(
            n for n in z.namelist() if n.startswith('word/media/')))
        for n in media_files:
            base = os.path.basename(n)
            with z.open(n) as fsrc, open(os.path.join(assets, base), 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst)

    ref_names = []  # 新檔名，對位 refs
    renamed = {}  # media/xxx -> 新檔名（同一檔被引用多次時重用同一新檔名）
    for k, (rid, media) in enumerate(refs, 1):
        if media in renamed:
            ref_names.append(renamed[media])
            continue
        ext = os.path.splitext(os.path.basename(media))[1].lstrip('.').lower()
        new = f'{stem}-image-{k}.{ext}'
        src = os.path.join(assets, os.path.basename(media))
        dst = os.path.join(assets, new)
        if os.path.exists(src):
            os.replace(src, dst)
        name = new if os.path.exists(dst) else None
        renamed[media] = name
        ref_names.append(name)

    print(f'引用圖片 {len(refs)} 張；media 實檔 {len(media_files)} 個')

    # ---- 2b. emf/wmf 轉 png（保留原檔），引用改指向 png ----
    with tempfile.TemporaryDirectory(prefix='emf2png-') as work:
        emf_png_map = convert_metafiles_to_png(assets, work)
    meta_ext = ('.emf', '.wmf')
    ref_names = [
        emf_png_map.get(name, name) if name and name.lower().endswith(meta_ext) else name
        for name in ref_names
    ]

    # ---- 2c. 群組示意圖文字標注（覆蓋原檔、一律 PNG；同一 media 只標注一次）----
    annotations, astats = group_text_boxes(xml)
    by_media = {}  # media/xxx -> 最終檔名
    for k, (rid, media) in enumerate(refs, 1):
        name = ref_names[k - 1]
        if name is None:
            continue
        if media in by_media:
            ref_names[k - 1] = by_media[media]
            continue
        group = annotations.get(rid)
        if group is not None:
            annotated = annotate_images.annotate(os.path.join(assets, name), group)
            if annotated is not None:
                if annotated != name:
                    old = os.path.join(assets, name)
                    if os.path.exists(old):
                        os.remove(old)  # 覆蓋式輸出：不留原始底圖檔
                name = annotated
        by_media[media] = name
        ref_names[k - 1] = name
    if astats['skipped']:
        print(f'警告: {astats["skipped"]} 個文字方塊未標注（不在可標注的群組中：'
              '無底圖／多底圖／旋轉不支援／群組外獨立方塊），文字仍保留在 md',
              file=sys.stderr)

    # ---- 3. 改寫 md：先拆相鄰佔位符，再依序換引用 ----
    with open(md_src, encoding='utf-8') as f:
        md = f.read()

    # 相鄰佔位符拆行（alt 可為空或帶 docx 圖片名，兩種形式都要拆）
    md = re.sub(r'\)\s*(!\[[^\]]*\]\(data:image/)', r')\n\n\1', md)

    placeholder = re.compile(r'!\[[^\]]*\]\(data:image/[^)]+\)')

    counter = {'n': 0}

    def sub_fn(m: re.Match) -> str:
        k = counter['n']
        counter['n'] += 1
        if k < len(ref_names) and ref_names[k]:
            # 路徑用 <> 包裹：檔名含空白或括號時仍是合法 CommonMark 連結；
            # alt 取自實際引用檔名，重複引用同一檔時 alt 仍與檔名一致
            alt = os.path.splitext(ref_names[k])[0]
            return f'![{alt}](<assets/{ref_names[k]}>)'
        return m.group(0)  # 引用不足：保留佔位符，靠數量核對回報

    md = placeholder.sub(sub_fn, md)

    md_path = os.path.join(outdir, f'{stem}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'替換佔位符 {counter["n"]} 個；引用 {len(ref_names)} 張')
    print(f'輸出: {md_path}')

    used = sum(1 for n in ref_names if n)
    if counter['n'] != len(ref_names) or counter['n'] != used:
        print(f'警告: 佔位符數 {counter["n"]} 與圖片引用數 {len(ref_names)} '
              f'（實抽 {used}）不一致，超出部分的佔位符未替換，請人工檢查',
              file=sys.stderr)
        return 2
    if any(n is None for n in ref_names):
        print('警告: 有引用在 media 中找不到對應檔案，已留下缺口', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
