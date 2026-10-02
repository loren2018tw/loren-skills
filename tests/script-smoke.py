#!/usr/bin/env python3
"""技能腳本跨平台煙霧測試（CI 與本機皆可跑）。

用法: python3 tests/script-smoke.py

涵蓋（不需重量級依賴；docx 全管線需 markitdown、標注驗證需 Pillow＋CJK 字型，
缺席時跳過對應段）:
  1. gimkit-to-blooket 轉換：成功輸出、逐題正確、CP950 pipe 不崩、來源錯誤 exit 1
  2. merge_md_images：成功對位、數量不符 exit 2、emf 轉檔失敗警告不崩
  3. annotate_images：群組示意圖文字繪回圖檔、字型無效時警告且原圖不動
  4. doc-to-md：docx 全管線（markitdown）、soffice 缺席 exit 1 含指引無 traceback、
     Pillow 缺席 exit 1 含安裝指令無 traceback

只用 Python 標準庫（Pillow 僅在可用時做像素驗證）；fixture（CSV、docx）在測試中
動態生成，不提交二進位檔。
"""
import base64
import csv
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'doc-to-markdown-with-image' / 'scripts'))
from _compat import common_tool_location, find_tool, use_utf8_stdio  # noqa: E402

use_utf8_stdio()  # 測試自身的輸出也要 UTF-8（Windows CI 的 pipe 預設 cp1252）

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


def solid_png(width: int, height: int, rgb=(255, 255, 255)) -> bytes:
    """純標準庫產生單色 PNG（標注驗證比對像素用）。"""
    raw = b''.join(b'\x00' + bytes(rgb) * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + tag + data + \
            struct.pack('>I', zlib.crc32(tag + data))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))

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


_GROUP_TEXT_P = ('<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
                 '<w:r><w:rPr><w:b/><w:color w:val="D22B2B"/><w:sz w:val="24"/>'
                 '</w:rPr><w:t>標籤文字</w:t></w:r></w:p>')

# 群組示意圖（Choice 的 wpg 群組＋Fallback 的 VML）：mammoth 讀 Fallback 分支
# 輸出圖片與文字，merge 端只解析 Choice 分支取座標。
_DOCUMENT_GROUP = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<w:body>
<w:p><w:r><w:t>測試段落。</w:t></w:r></w:p>
<w:p><w:r>
<mc:AlternateContent>
<mc:Choice Requires="wpg">
<w:drawing><wp:inline>
<wp:extent cx="914400" cy="914400"/><wp:docPr id="1" name="group"/>
<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup">
<wpg:wgp>
<wpg:cNvGrpSpPr/><wpg:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/><a:chOff x="0" y="0"/><a:chExt cx="914400" cy="914400"/></a:xfrm></wpg:grpSpPr>
<pic:pic><pic:nvPicPr><pic:cNvPr id="2" name="image1.ext"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rId5"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>
<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="57150" y="80010"/><a:ext cx="800100" cy="685800"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></wps:spPr>
<wps:txbx><w:txbxContent>{_GROUP_TEXT_P}</w:txbxContent></wps:txbx>
<wps:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/></wps:wsp>
</wpg:wgp></a:graphicData></a:graphic>
</wp:inline></w:drawing>
</mc:Choice>
<mc:Fallback>
<w:pict>
<v:group id="g1" style="position:absolute;width:72pt;height:72pt" coordorigin="0,0" coordsize="100,100">
<v:shape id="s1" style="position:absolute;left:0;top:0;width:100;height:100" type="_x0000_t75">
<v:imagedata r:id="rId6" o:title=""/>
</v:shape>
<v:shape id="s2" style="position:absolute;left:10;top:10;width:40;height:20" stroked="f">
<v:textbox inset="0,0,0,0"><w:txbxContent>{_GROUP_TEXT_P}</w:txbxContent></v:textbox>
</v:shape>
</v:group>
</w:pict>
</mc:Fallback>
</mc:AlternateContent>
</w:r></w:p>
<w:sectPr/>
</w:body></w:document>'''


def build_group_docx(path: Path, media_name: str, media_bytes: bytes) -> None:
    """最小群組示意圖 docx：Choice 的 wpg 群組（底圖＋文字方塊）與 Fallback 的 VML。"""
    doc_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{media_name}"/>
<Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{media_name}"/>
</Relationships>'''
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', _ROOT_RELS)
        z.writestr('word/document.xml', _DOCUMENT_GROUP)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr(f'word/media/{media_name}', media_bytes)


PLACEHOLDER = '![](data:image/png;base64...)'


def write_md(path: Path, placeholders: int) -> None:
    body = '測試段落。\n\n' + '\n\n'.join([PLACEHOLDER] * placeholders) + '\n'
    path.write_text(body, encoding='utf-8')


def tool_discoverable(name: str) -> bool:
    """近似腳本的工具搜尋：PATH 或常見安裝位置。"""
    return find_tool(name) is not None


_PILLOW = None


def pillow_available() -> bool:
    """本機是否有 Pillow（本 skill 必要依賴；缺席時相關段跳過）。"""
    global _PILLOW
    if _PILLOW is None:
        _PILLOW = _module_available('PIL')
    return _PILLOW


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
    if not pillow_available():
        skip('merge: 全套', '本機沒有 Pillow（本 skill 必要依賴）')
        return
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


def test_overlay(tmp: Path) -> None:
    if not pillow_available():
        skip('overlay: 全套', '本機沒有 Pillow（本 skill 必要依賴）')
        return
    src = solid_png(80, 80)
    # 1) 群組示意圖：文字繪回底圖（覆蓋原檔、一律 PNG；圖下文字保留）
    d = tmp / 'overlay1'
    d.mkdir()
    build_group_docx(d / 'demo.docx', 'image1.png', src)
    write_md(d / 'markitdown.md', 1)
    r = run([sys.executable, str(MERGE), str(d / 'demo.docx'),
             str(d / 'markitdown.md'), str(d / 'out')])
    text = out_text(r)
    md_file = d / 'out' / 'demo.md'
    md = md_file.read_text(encoding='utf-8') if md_file.is_file() else ''
    img = d / 'out' / 'assets' / 'demo-image-1.png'
    check('overlay: exit 0', r.returncode == 0, text[-500:])
    check('overlay: md 引用標注後的 PNG',
          '![demo-image-1](<assets/demo-image-1.png>)' in md, md)
    check('overlay: 標注圖存在', img.is_file())
    if '找不到可用的 CJK 字型' in text:
        if sys.platform.startswith('linux'):
            check('overlay: Linux 應找得到 CJK 字型完成標注', False, text[-400:])
        else:
            skip('overlay: 像素驗證', '本機找不到 CJK 字型')
    else:
        from PIL import Image  # 僅在 Pillow 可用時載入
        with Image.open(img) as annotated:
            raw = annotated.convert('RGB').tobytes()
        white = b'\xff\xff\xff'
        check('overlay: 圖片已繪入文字（像素改變）',
              any(raw[i:i + 3] != white for i in range(0, len(raw), 3)))
    # 2) DOC2MD_FONT 指向不存在的字型 → 警告、跳過標注、原圖不動、exit 0
    d2 = tmp / 'overlay2'
    d2.mkdir()
    build_group_docx(d2 / 'demo.docx', 'image1.png', src)
    write_md(d2 / 'markitdown.md', 1)
    r = run([sys.executable, str(MERGE), str(d2 / 'demo.docx'),
             str(d2 / 'markitdown.md'), str(d2 / 'out')],
            env={'DOC2MD_FONT': str(tmp / 'no-such-font.ttf')})
    text = out_text(r)
    img2 = d2 / 'out' / 'assets' / 'demo-image-1.png'
    check('overlay: 字型無效時警告、exit 0、原圖不變',
          r.returncode == 0 and '字型' in text and img2.is_file()
          and img2.read_bytes() == src, text[-400:])


def test_doc2md(tmp: Path) -> None:
    # 1) docx 全管線（需 markitdown 與 Pillow；缺席跳過）
    if not pillow_available():
        skip('doc-to-md: docx 全管線', '本機沒有 Pillow（本 skill 必要依賴）')
    elif not tool_discoverable('markitdown') and not _module_available('markitdown'):
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
        # 1b) 群組示意圖全管線：標注 PNG＋圖下文字仍在（mammoth 讀 Fallback 分支）
        d2 = tmp / 'pipeline-group'
        d2.mkdir()
        build_group_docx(d2 / 'group.docx', 'image2.png', solid_png(80, 80))
        r = run([sys.executable, str(DOC2MD), str(d2 / 'group.docx')])
        md2_file = d2 / 'group' / 'group.md'
        md2 = md2_file.read_text(encoding='utf-8') if md2_file.is_file() else ''
        check('doc-to-md: 群組示意圖管線（標注 PNG、圖下文字仍在）',
              r.returncode == 0
              and '![group-image-1](<assets/group-image-1.png>)' in md2
              and '標籤文字' in md2, (out_text(r)[-300:] + md2))
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
    # 4) Pillow 缺席 → exit 1、含安裝指令、無 traceback
    #    （-S 跳過 site-packages 確定性觸發；需確定 markitdown 檢查會先通過）
    if not tool_discoverable('markitdown'):
        skip('doc-to-md: Pillow 缺席指引', '本機找不到 markitdown，無法越過前一關')
        return
    d = tmp / 'absent-pillow'
    d.mkdir()
    build_docx(d / 'fixture.docx', 'image1.png', PNG_1PX)
    r = run([sys.executable, '-S', str(DOC2MD), str(d / 'fixture.docx')])
    text = out_text(r)
    check('doc-to-md: Pillow 缺席 exit 1、含安裝指令、無 traceback',
          r.returncode == 1 and 'Pillow' in text and 'pip install' in text
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
        test_overlay(tmp)
        test_doc2md(tmp)
    print(f'\n通過 {len(PASSED)}、失敗 {len(FAILED)}、跳過 {len(SKIPPED)}')
    if FAILED:
        for name, detail in FAILED:
            print(f'  [FAIL] {name}: {detail}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
