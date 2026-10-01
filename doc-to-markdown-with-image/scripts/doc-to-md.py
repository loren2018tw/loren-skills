#!/usr/bin/env python3
"""將 Word 文件（.docx / 舊版 .doc）轉成 markdown，抽出圖片為媒體資產。

管線: [soffice 橋接] → markitdown 全文（圖=佔位符）→ merge_md_images.py 還原圖檔
用法: doc-to-md.py <來源文件> [輸出資料夾]

直譯器呼叫（見 SKILL.md）：Windows 用 py -3、macOS/Linux 用 python3。
只用 Python 標準庫；.docx 不需 soffice（.doc 橋接與 emf/wmf 轉檔才需要）。
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _compat import find_tool, use_utf8_stdio  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent


def fail(msg):
    print(msg, file=sys.stderr)
    return 1


def resolve_markitdown():
    """回傳 markitdown 呼叫前綴（list）；找不到回 None。"""
    exe = find_tool('markitdown')
    if exe:
        return [exe]
    if importlib.util.find_spec('markitdown') is not None:
        return [sys.executable, '-m', 'markitdown']
    return None


def main(argv):
    use_utf8_stdio()
    if len(argv) not in (2, 3):
        return fail(f'用法: {Path(argv[0]).name} <來源文件> [輸出資料夾]')
    src = Path(argv[1])
    if not src.is_file():
        return fail(f'找不到來源文件: {src}')
    src = src.resolve()
    stem = src.stem
    ext = src.suffix.lower().lstrip('.')

    if ext == 'doc':
        soffice = find_tool('soffice')
        if soffice is None:
            return fail('需要 LibreOffice（soffice）進行 .doc 橋接。安裝: '
                        'winget install -e --id TheDocumentFoundation.LibreOffice（Windows）／'
                        'brew install --cask libreoffice（macOS）／發行版套件（Linux）；'
                        '或確認 soffice 在 PATH')
    elif ext != 'docx':
        return fail(f'只支援 .docx / .doc，收到: .{ext}')

    markitdown_cmd = resolve_markitdown()
    if markitdown_cmd is None:
        return fail("需要 markitdown: uv tool install 'markitdown[docx]'"
                    "（或 pip install 'markitdown[docx]'）")

    outdir = Path(argv[2]) if len(argv) == 3 else src.parent / stem
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='doc2md-') as work:
        workdir = Path(work)
        docx = src
        if ext == 'doc':
            r = subprocess.run(
                [soffice, f'-env:UserInstallation={(workdir / "lo").as_uri()}',
                 '--headless', '--convert-to', 'docx:MS Word 2007 XML',
                 '--outdir', str(workdir), str(src)],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            docx = workdir / f'{stem}.docx'
            if not docx.is_file():
                return fail(f'LibreOffice 轉檔失敗: {src}\n{r.stdout}{r.stderr}')

        md_tmp = workdir / 'markitdown.md'
        r = subprocess.run([*markitdown_cmd, str(docx), '-o', str(md_tmp)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0 or not md_tmp.is_file():
            return fail('markitdown 轉換失敗:\n' + (r.stderr or r.stdout or ''))

        merge = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / 'merge_md_images.py'),
             str(docx), str(md_tmp), str(outdir)])
        if merge.returncode != 0:
            return merge.returncode  # 2 = 佔位符對位警告（merge 已印出細節）

    print(outdir / f'{stem}.md')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
