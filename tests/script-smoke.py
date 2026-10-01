#!/usr/bin/env python3
"""技能腳本跨平台煙霧測試（CI 與本機皆可跑）。

用法: python3 tests/script-smoke.py

涵蓋（不需重量級依賴；docx 全管線需 markitdown，缺席時跳過該段）:
  1. gimkit-to-blooket 轉換：成功輸出、逐題正確、CP950 pipe 不崩、來源錯誤 exit 1
  2. merge_md_images：成功對位、數量不符 exit 2、emf 轉檔失敗警告不崩
  3. doc-to-md：docx 全管線（markitdown）、soffice 缺席 exit 1 含指引無 traceback

只用 Python 標準庫；fixture（CSV、docx）在測試中動態生成，不提交二進位檔。
"""
import base64
import csv
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'doc-to-markdown-with-image' / 'scripts'))
from _compat import common_tool_location, find_tool  # noqa: E402

BLOOKET = ROOT / 'gimkit-to-blooket' / 'scripts' / 'convert_to_blooket.py'
MERGE = ROOT / 'doc-to-markdown-with-image' / 'scripts' / 'merge_md_images.py'
DOC2MD = ROOT / 'doc-to-markdown-with-image' / 'scripts' / 'doc-to-md.py'

PASSED = []
FAILED = []
SKIPPED = []


def check(name: str, ok: bool, detail: str = '') -> bool:
    if ok:
        PASSED.append(name)
        print(f'[PASS] {name}')
    else:
        FAILED.append((name, detail))
        print(f'[FAIL] {name}' + (f' — {detail}' if detail else ''))
    return ok


def skip(name: str, reason: str) -> None:
    SKIPPED.append((name, reason))
    print(f'[SKIP] {name} — {reason}')


def run(cmd, env=None, cwd=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, capture_output=True, cwd=cwd, env=e)


def out_text(r: subprocess.CompletedProcess) -> str:
    return (r.stdout + r.stderr).decode('utf-8', errors='replace')


# ---------- fixture 生成 ----------

def write_gimkit_csv(path: Path) -> list[list[str]]:
    rows = [
        ['Question', 'Correct Answer', 'Incorrect Answer 1', 'Incorrect Answer 2', 'Incorrect Answer 3'],
        ['颱風為什麼會形成？', '因為溫暖海水提供能量', '因為冷空氣下沉', '因為地球自轉速度', '因為山脈阻擋'],
        ['板塊交界處常發生什麼？', '地震', '沙塵暴', '乾旱', '寒流'],
    ]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
    return rows


PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')

_CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Default Extension="emf" ContentType="image/x-emf"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

_ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

_DOCUMENT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
<w:body>
<w:p><w:r><w:t>測試段落。</w:t></w:r></w:p>
<w:p><w:r><w:drawing><wp:inline>
<wp:extent cx="914400" cy="914400"/><wp:docPr id="1" name="Picture 1"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic><pic:nvPicPr><pic:cNvPr id="1" name="image1.ext"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rId5"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
<w:sectPr/>
</w:body></w:document>'''


def build_docx(path: Path, media_name: str, media_bytes: bytes) -> None:
    """最小 docx：一段文字 + 一張內嵌圖片（引用序與 media 一致）。"""
    doc_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{media_name}"/>
</Relationships>'''
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', _ROOT_RELS)
        z.writestr('word/document.xml', _DOCUMENT)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr(f'word/media/{media_name}', media_bytes)


PLACEHOLDER = '![](data:image/png;base64...)'


def write_md(path: Path, placeholders: int) -> None:
    body = '測試段落。\n\n' + '\n\n'.join([PLACEHOLDER] * placeholders) + '\n'
    path.write_text(body, encoding='utf-8')


def tool_discoverable(name: str) -> bool:
    """近似腳本的工具搜尋：PATH 或常見安裝位置。"""
    return find_tool(name) is not None


# ---------- 測試 ----------

def test_blooket(tmp: Path) -> None:
    rows = write_gimkit_csv(tmp / 'src.csv')
    out = tmp / 'out.csv'
    # 1) 成功（同時驗證 CP950 pipe 不崩：zh-TW Windows 的預設 pipe 編碼）
    r = run([sys.executable, str(BLOOKET), str(tmp / 'src.csv'), '-o', str(out)],
            env={'PYTHONIOENCODING': 'cp950'})
    check('blooket: exit 0', r.returncode == 0, out_text(r)[-500:])
    try:
        stdout = r.stdout.decode('utf-8')
    except UnicodeDecodeError as e:
        stdout = ''
        check('blooket: stdout 可解為 UTF-8（CP950 pipe 不崩）', False, str(e))
    else:
        check('blooket: stdout 可解為 UTF-8（CP950 pipe 不崩）', True)
    check('blooket: 驗證訊息存在', '通過' in stdout, stdout[-300:])
    if out.is_file():
        with open(out, newline='', encoding='utf-8-sig') as f:
            data = [row for row in csv.reader(f)][2:]  # 跳過前兩列範本表頭
        ok = len(data) == len(rows) - 1
        for i, (row, src_row) in enumerate(zip(data, rows[1:]), start=1):
            pos = int(row[7])
            ok = ok and row[1] == src_row[0] and row[2 + pos - 1] == src_row[1]
            ok = ok and sorted(row[2:6]) == sorted(src_row[1:5]) and row[6] == '30'
        check('blooket: 輸出逐題正確（正解位置、選項集合、Time Limit）', ok)
    else:
        check('blooket: 輸出檔存在', False, '找不到 ' + str(out))
    # 2) 來源錯誤 → exit 1
    bad = tmp / 'bad.csv'
    bad.write_text('Question,Correct Answer\n只有一題,而且缺欄\n', encoding='utf-8')
    r = run([sys.executable, str(BLOOKET), str(bad)])
    check('blooket: 來源錯誤 exit 1 且訊息含「檢查未通過」',
          r.returncode == 1 and '檢查未通過' in out_text(r), out_text(r)[-300:])


def test_merge(tmp: Path) -> None:
    # 1) 成功對位
    d = tmp / 'merge1'
    d.mkdir()
    build_docx(d / 'demo.docx', 'image1.png', PNG_1PX)
    write_md(d / 'markitdown.md', 1)
    r = run([sys.executable, str(MERGE), str(d / 'demo.docx'), str(d / 'markitdown.md'), str(d / 'out')])
    md = (d / 'out' / 'demo.md').read_text(encoding='utf-8') if (d / 'out' / 'demo.md').is_file() else ''
    check('merge: exit 0', r.returncode == 0, out_text(r)[-500:])
    check('merge: 圖片抽出並改名', (d / 'out' / 'assets' / 'demo-image-1.png').is_file())
    check('merge: md 引用正確且無 data:image 殘留',
          '![demo-image-1](<assets/demo-image-1.png>)' in md and 'data:image' not in md, md)
    # 2) 數量不符 → exit 2
    d2 = tmp / 'merge2'
    d2.mkdir()
    build_docx(d2 / 'demo.docx', 'image1.png', PNG_1PX)
    write_md(d2 / 'markitdown.md', 2)
    r = run([sys.executable, str(MERGE), str(d2 / 'demo.docx'), str(d2 / 'markitdown.md'), str(d2 / 'out')])
    check('merge: 佔位符數不符 exit 2', r.returncode == 2, out_text(r)[-300:])
    # 3) emf 且 soffice 缺席 → 警告但不崩（以空 PATH 確定性觸發；常見安裝位置有 soffice 時跳過）
    if common_tool_location('soffice'):
        skip('merge: emf soffice 缺席警告', '本機常見安裝位置可找到 soffice')
    else:
        d3 = tmp / 'merge3'
        d3.mkdir()
        empty = tmp / 'empty-path'
        empty.mkdir()
        build_docx(d3 / 'demo.docx', 'image1.emf', b'not a real emf')
        write_md(d3 / 'markitdown.md', 1)
        r = run([sys.executable, str(MERGE), str(d3 / 'demo.docx'), str(d3 / 'markitdown.md'), str(d3 / 'out')],
                env={'PATH': str(empty)})
        md3 = (d3 / 'out' / 'demo.md').read_text(encoding='utf-8') if (d3 / 'out' / 'demo.md').is_file() else ''
        check('merge: emf 且 soffice 缺席時僅警告、exit 0、引用保留 .emf',
              r.returncode == 0 and '警告' in out_text(r) and 'demo-image-1.emf' in md3, out_text(r)[-300:])


def test_doc2md(tmp: Path) -> None:
    # 1) docx 全管線（需 markitdown；缺席跳過）
    if not tool_discoverable('markitdown') and not _module_available('markitdown'):
        skip('doc-to-md: docx 全管線', '本機找不到 markitdown')
    else:
        d = tmp / 'pipeline'
        d.mkdir()
        build_docx(d / 'fixture.docx', 'image1.png', PNG_1PX)
        r = run([sys.executable, str(DOC2MD), str(d / 'fixture.docx')])
        md = (d / 'fixture' / 'fixture.md').read_text(encoding='utf-8') if (d / 'fixture' / 'fixture.md').is_file() else ''
        check('doc-to-md: docx 管線 exit 0', r.returncode == 0, out_text(r)[-500:])
        check('doc-to-md: md 與圖片產物正確、無 data:image 殘留',
              '![fixture-image-1](<assets/fixture-image-1.png>)' in md
              and (d / 'fixture' / 'assets' / 'fixture-image-1.png').is_file()
              and 'data:image' not in md, md)
        last_line = r.stdout.decode('utf-8', 'replace').strip().splitlines()[-1:] or ['']
        check('doc-to-md: 成功時印出 md 路徑',
              last_line[0].endswith('fixture.md'),
              r.stdout.decode('utf-8', 'replace')[-200:])
    # 2) soffice 缺席 → exit 1、含安裝指引、無 traceback（以空 PATH 確定性觸發；常見安裝位置有 soffice 時跳過）
    if common_tool_location('soffice'):
        skip('doc-to-md: soffice 缺席指引', '本機常見安裝位置可找到 soffice')
    else:
        d = tmp / 'absent'
        d.mkdir()
        (d / 'fake.doc').write_bytes(b'not a real doc')
        empty = tmp / 'empty-path'
        empty.mkdir(exist_ok=True)
        r = run([sys.executable, str(DOC2MD), str(d / 'fake.doc')], env={'PATH': str(empty)})
        text = out_text(r)
        check('doc-to-md: soffice 缺席 exit 1、含安裝指引、無 traceback',
              r.returncode == 1 and 'LibreOffice' in text and 'Traceback' not in text, text[-400:])
    # 3) markitdown 缺席 → exit 1、含可執行安裝指令、無 traceback
    #    （空 PATH + 空 HOME/USERPROFILE + -S 跳過 site-packages，三平台皆確定性觸發）
    d = tmp / 'absent-md'
    d.mkdir()
    build_docx(d / 'fixture.docx', 'image1.png', PNG_1PX)
    empty = tmp / 'empty-path'
    empty.mkdir(exist_ok=True)
    emptyhome = tmp / 'empty-home'
    emptyhome.mkdir(exist_ok=True)
    r = run([sys.executable, '-S', str(DOC2MD), str(d / 'fixture.docx')],
            env={'PATH': str(empty), 'HOME': str(emptyhome), 'USERPROFILE': str(emptyhome)})
    text = out_text(r)
    check('doc-to-md: markitdown 缺席 exit 1、含安裝指令、無 traceback',
          r.returncode == 1 and 'markitdown' in text and 'uv tool install' in text
          and 'Traceback' not in text, text[-400:])


def _module_available(name: str) -> bool:
    try:
        return subprocess.run([sys.executable, '-c', f'import {name}'],
                              capture_output=True).returncode == 0
    except OSError:
        return False


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='skill-smoke-') as td:
        tmp = Path(td)
        test_blooket(tmp)
        test_merge(tmp)
        test_doc2md(tmp)
    print(f'\n通過 {len(PASSED)}、失敗 {len(FAILED)}、跳過 {len(SKIPPED)}')
    if FAILED:
        for name, detail in FAILED:
            print(f'  [FAIL] {name}: {detail}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
