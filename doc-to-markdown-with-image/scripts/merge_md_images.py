#!/usr/bin/env python3
"""把 markitdown 輸出的 md 中圖片佔位符，還原成 docx 內的真實圖檔。

用法: merge_md_images.py <docx> <markitdown.md> <輸出目錄>

原理:
  markitdown（mammoth）轉 docx 時，圖片變成截斷的 data URI 佔位符
  `![](data:image/jpeg;base64...)`，且佔位符數量與 docx 內圖片引用數一致、
  順序同 body 順序。本腳本依 docx `word/document.xml` 中 mc:Choice 分支的
  r:embed/r:id 引用順序（跳過 mc:Fallback 避免重複），把第 k 個佔位符
  換成第 k 張圖：`![<stem>-image-k](assets/<stem>-image-k.<ext>)`。

  `.emf/.wmf` 向量圖另以 soffice 轉高解析 png（原檔保留在 assets 備查），
  md 引用指向 png；轉換失敗時引用維持原格式。

  只用 Python 標準庫，不需任何第三方套件。

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

    if shutil.which('soffice') is None:
        print('警告: 找不到 soffice，無法將 emf/wmf 轉 png，引用保留原格式',
              file=sys.stderr)
        return {}

    renamed = {}
    for f in targets:
        src = os.path.join(assets, f)
        r = subprocess.run(
            ['soffice', f'-env:UserInstallation=file://{work}/lo',
             '--headless', '--convert-to', PNG_FILTER,
             '--outdir', assets, src],
            capture_output=True, text=True, timeout=120)
        png = os.path.splitext(src)[0] + '.png'
        if r.returncode == 0 and os.path.exists(png):
            # <stem>-image-K.emf → <stem>-image-K.png；emf/wmf 原檔留著備查
            renamed[f] = os.path.basename(png)
        else:
            print(f'警告: emf/wmf 轉 png 失敗: {f}（引用保留原檔）', file=sys.stderr)
    return renamed


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 1
    docx, md_src, outdir = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/')
    stem = os.path.splitext(os.path.basename(docx))[0]
    assets = os.path.join(outdir, 'assets')
    os.makedirs(assets, exist_ok=True)
    work = tempfile.mkdtemp(prefix='emf2png-')

    # ---- 1. docx: body 順序的圖片引用（只掃 mc:Choice，跳過 mc:Fallback）----
    with zipfile.ZipFile(docx) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
        rmap = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(media/[^"]+)"', rels))
        refs = []  # [(rId, media/xxx), ...] 依 body 順序
        i = 0
        while i < len(xml):
            fb = xml.find('<mc:Fallback>', i)
            seg_end = fb if fb != -1 else len(xml)
            for m in re.finditer(r'(?:r:embed|r:id)="(rId\d+)"', xml[i:seg_end]):
                rid = m.group(1)
                if rid in rmap:
                    refs.append((rid, rmap[rid]))
            if fb == -1:
                break
            end = xml.find('</mc:Fallback>', fb)
            i = end + len('</mc:Fallback>') if end != -1 else len(xml)

        # ---- 2. 抽出 media 至 assets/，並依引用順序改名 ----
        media_files = sorted(set(
            n for n in z.namelist() if n.startswith('word/media/')))
        for n in media_files:
            base = os.path.basename(n)
            with z.open(n) as fsrc, open(os.path.join(assets, base), 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst)

    ref_names = []  # 新檔名，對位 refs
    for k, (rid, media) in enumerate(refs, 1):
        ext = os.path.splitext(os.path.basename(media))[1].lstrip('.').lower()
        new = f'{stem}-image-{k}.{ext}'
        src = os.path.join(assets, os.path.basename(media))
        dst = os.path.join(assets, new)
        if os.path.exists(src):
            os.replace(src, dst)
        ref_names.append(new if os.path.exists(dst) else None)

    print(f'引用圖片 {len(refs)} 張；media 實檔 {len(media_files)} 個')

    # ---- 2b. emf/wmf 轉 png（保留原檔），引用改指向 png ----
    renamed = convert_metafiles_to_png(assets, work)
    meta_ext = ('.emf', '.wmf')
    ref_names = [
        renamed.get(name) if name and name.lower().endswith(meta_ext) else name
        for name in ref_names
    ]

    # ---- 3. 改寫 md：先拆相鄰佔位符，再依序換引用 ----
    with open(md_src, encoding='utf-8') as f:
        md = f.read()

    # 相鄰佔位符拆行（此時格式固定為 data:...，不會誤傷一般連結）
    md = re.sub(r'\)\s*(!\[\]\(data:image/)', r')\n\n\1', md)

    placeholder = re.compile(r'!\[\]\(data:image/[^)]+\)')

    counter = {'n': 0}

    def sub_fn(m: re.Match) -> str:
        k = counter['n']
        counter['n'] += 1
        if k < len(ref_names) and ref_names[k]:
            # 路徑用 <> 包裹：檔名含空白或括號時仍是合法 CommonMark 連結
            alt = f'{stem}-image-{k + 1}'
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
