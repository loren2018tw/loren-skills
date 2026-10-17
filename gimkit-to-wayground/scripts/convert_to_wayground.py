#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GimKit CSV → Wayground（原 Quizizz）試算表匯入格式（.xlsx）轉換器。

來源格式（GimKit 匯出，5 欄）:
    Question, Correct Answer, Incorrect Answer 1, Incorrect Answer 2, Incorrect Answer 3

輸出格式（複刻 Wayground 官方範本 "Wayground Assessment Template.xlsx" 幾何，
單一工作表 "Create a Quiz"）:
    第 1 列 = 表頭: A=Question Text, B=Question Type, C~G=Option 1~5,
                     H=Correct Answer, I=Time in seconds, J=Image Link,
                     K=Answer explanation
    第 2 列 = 範本的說明列，留空
    第 3 列起 = 資料: A=題目, B=Multiple Choice, C~F=四個選項, G 留空,
                       H=正解選項編號 1~4, I=秒數, J/K 留空

用法:
    Windows:      py -3 scripts/convert_to_wayground.py 來源GimKit.csv [-o 輸出檔.xlsx] [--time 30]
    macOS/Linux:  python3 scripts/convert_to_wayground.py 來源GimKit.csv [-o 輸出檔.xlsx] [--time 30]
"""
import argparse
import collections
import csv
import sys
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

SHEET_NAME = "Create a Quiz"  # 官方範本的工作表名
HEADER_ROW = 1  # 官方範本: 表頭在第 1 列
FIRST_DATA_ROW = 3  # 官方範本: 第 2 列為說明列，資料自第 3 列起（資料驗證範圍 B3:B1000）

QUESTION_TYPE = "Multiple Choice"  # 範本 B 欄下拉的第一個值，也是預設題型
DEFAULT_TIME = 30  # 範本 I 欄註明 "(optional, default value is 30 seconds)"
# 範本 I3:I1000 的資料驗證下拉值
TIME_CHOICES = (5, 10, 20, 30, 45, 60, 120, 180, 300, 900)
# 範本 B3:B1000 的題型下拉值（本工具只產 Multiple Choice）
QUESTION_TYPES = (
    "Multiple Choice", "Checkbox", "Fill-in-the-Blank", "Open-Ended",
    "Poll", "Draw", "Reorder", "Match",
)

HEADER_CELLS = [
    "Question Text",
    "Question Type",
    "Option 1",
    "Option 2",
    "Option 3",
    "Option 4",
    "Option 5",
    "Correct Answer",
    "Time in seconds",
    "Image Link",
    "Answer explanation",
]

_CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

_ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

_ZIP_DATE = (1980, 1, 1, 0, 0, 0)  # 固定時間戳: 同樣輸入產出位元組相同的檔案


def use_utf8_stdio() -> None:
    """stdout/stderr 明確以 UTF-8 輸出：非 UTF-8 pipe（如 zh-TW Windows 的 CP950）不崩。

    與 doc-to-markdown-with-image/scripts/_compat.py 的同名函式刻意重複：
    各技能需能獨立安裝，不互相 import。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def fail(msg: str) -> None:
    sys.stdout.flush()
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def col_letter(index: int) -> str:
    """1-based 欄序 → Excel 欄名（1=A, 2=B, …）。本工具只用到 A~K。"""
    name = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def read_source(path: str) -> list[list[str]]:
    """讀取 GimKit 來源 CSV，驗證欄數、空欄與選項重複，回傳資料列（不含表頭）。"""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    if len(rows) < 2:
        fail(f"{path} 沒有任何題目資料（只有表頭或空檔）")
    header, data = rows[0], rows[1:]
    print(f"來源: {path}")
    print(f"  表頭: {header}")
    print(f"  題數: {len(data)}")
    problems = []
    for i, r in enumerate(data, start=1):
        if len(r) != 5:
            problems.append(f"  第 {i} 題有 {len(r)} 欄（預期 5 欄，請確認來源格式）")
            continue
        for col, value in enumerate(r):
            if not value.strip():
                problems.append(f"  第 {i} 題第 {col + 1} 欄為空")
        options = [c.strip() for c in r[1:5]]
        if len(set(options)) != 4:
            problems.append(f"  第 {i} 題選項有重複（正解與錯誤選項不可相同）")
    if problems:
        fail("來源檔欄位檢查未通過:\n" + "\n".join(problems))
    return data


def convert(data: list[list[str]], time_limit: int) -> list[tuple[str, list[str], int]]:
    """正解位置輪替 1→2→3→4，回傳每題 (題目, 四選項, 正解欄號)。"""
    out_rows = []
    for i, r in enumerate(data, start=1):
        question, correct = r[0].strip(), r[1].strip()
        others = [c.strip() for c in r[2:5]]
        # 來源正解固定在第 2 欄；照抄會讓正解永遠落在 Option 1，
        # 因此主動輪替，讓教師在 Wayground 編輯器檢查時看到正解分散。
        pos = (i - 1) % 4 + 1
        answers = others[: pos - 1] + [correct] + others[pos - 1 :]
        out_rows.append((question, answers, pos))
    return out_rows


def _clean(text: str) -> str:
    """移除 XML 不允許的控制字元（保留 tab 與換行），再跳脫 & < >。"""
    kept = [c for c in text if c in "\t\n" or c >= " "]
    return escape("".join(kept))


def _cell(ref: str, value: object, numeric: bool = False) -> str:
    if numeric:
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{_clean(str(value))}</t></is></c>'


def _sheet_xml(rows: list[tuple[str, list[str], int]], time_limit: int) -> str:
    """組出 sheet1.xml：表頭在第 1 列、資料自第 3 列起（比照範本資料驗證範圍）。"""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{NS_MAIN}"><sheetData>',
    ]
    cells = [_cell(f"{col_letter(1 + k)}{HEADER_ROW}", text) for k, text in enumerate(HEADER_CELLS)]
    parts.append(f'<row r="{HEADER_ROW}">{"".join(cells)}</row>')
    for i, (question, answers, pos) in enumerate(rows, start=1):
        r = FIRST_DATA_ROW + i - 1
        row = [
            _cell(f"A{r}", question),
            _cell(f"B{r}", QUESTION_TYPE),
        ]
        row += [_cell(f"{col_letter(3 + k)}{r}", text) for k, text in enumerate(answers)]
        # G 欄 Option 5、J 欄 Image Link、K 欄 Answer explanation 一律留空
        row += [
            _cell(f"H{r}", pos, numeric=True),
            _cell(f"I{r}", time_limit, numeric=True),
        ]
        parts.append(f'<row r="{r}">{"".join(row)}</row>')
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def write_xlsx(rows: list[tuple[str, list[str], int]], time_limit: int, path: str) -> None:
    """以標準庫寫出最小 xlsx（無樣式、字串用 inlineStr，不需 sharedStrings）。"""
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{NS_MAIN}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="{escape(SHEET_NAME)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''
    parts = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _ROOT_RELS,
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": workbook_rels,
        "xl/worksheets/sheet1.xml": _sheet_xml(rows, time_limit),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, _ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, text.encode("utf-8"))


def read_xlsx(path: str) -> tuple[dict[int, dict[str, str]], str]:
    """重讀產出的 xlsx，回傳（{列號: {欄名: 值}}, 工作表名）（驗證用）。"""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheet_name = next(wb.iter(f"{{{NS_MAIN}}}sheet")).get("name")
    table: dict[int, dict[str, str]] = {}
    for row in root.iter(f"{{{NS_MAIN}}}row"):
        cells = {}
        for cell in row:
            ref = cell.get("r")
            col = "".join(ch for ch in ref if ch.isalpha())
            if cell.get("t") == "inlineStr":
                node = cell.find(f"{{{NS_MAIN}}}is/{{{NS_MAIN}}}t")
            else:
                node = cell.find(f"{{{NS_MAIN}}}v")
            cells[col] = node.text if node is not None and node.text is not None else ""
        table[int(row.get("r"))] = cells
    return table, sheet_name


def verify(path: str, src: list[list[str]], time_limit: int) -> None:
    """重讀產出的 xlsx，比對工作表名、表頭列位與逐題內容。"""
    table, sheet_name = read_xlsx(path)
    errs = []
    if sheet_name != SHEET_NAME:
        errs.append(f"工作表名 = {sheet_name!r}（官方範本為 {SHEET_NAME!r}）")
    expected_rows = [HEADER_ROW] + list(range(FIRST_DATA_ROW, FIRST_DATA_ROW + len(src)))
    if sorted(table) != expected_rows:
        fail(f"驗證失敗: 產出檔列號 {sorted(table)} ≠ 預期 {expected_rows}")
    if table[HEADER_ROW] != {col_letter(1 + k): t for k, t in enumerate(HEADER_CELLS)}:
        errs.append(f"表頭（第 {HEADER_ROW} 列）與官方範本不符: {table[HEADER_ROW]}")
    pos_dist = collections.Counter()
    for i, s in enumerate(src, start=1):
        cells = table[FIRST_DATA_ROW + i - 1]
        question, correct = s[0].strip(), s[1].strip()
        answers = [cells.get(col_letter(3 + k), "") for k in range(4)]
        pos_text = cells.get("H", "")
        if cells.get("A") != question:
            errs.append(f"第 {i} 題: 題目文字不符")
        if cells.get("B") != QUESTION_TYPE:
            errs.append(f"第 {i} 題: Question Type = {cells.get('B')!r}")
        if any(cells.get(col) for col in ("G", "J", "K")):
            errs.append(f"第 {i} 題: Option 5／Image Link／Answer explanation 應留空")
        if cells.get("I") != str(time_limit):
            errs.append(f"第 {i} 題: Time in seconds = {cells.get('I')!r}（應為 {time_limit}）")
        if pos_text not in ("1", "2", "3", "4"):
            errs.append(f"第 {i} 題: Correct Answer = {pos_text!r}")
            continue
        pos = int(pos_text)
        pos_dist[pos] += 1
        if answers[pos - 1] != correct:
            errs.append(f"第 {i} 題: 編號 {pos} 的選項不是正解")
        if sorted(answers) != sorted(x.strip() for x in s[1:5]):
            errs.append(f"第 {i} 題: 選項集合與來源不符")
    if errs:
        fail("驗證失敗:\n" + "\n".join(errs))
    print("驗證: ✅ 重讀產出檔（xlsx）逐題比對通過，與來源一致")
    print(f"驗證: 正解欄號分布 = {dict(sorted(pos_dist.items()))}")
    print(f"驗證: Time in seconds 全為 {time_limit} 秒")


def main() -> None:
    use_utf8_stdio()
    ap = argparse.ArgumentParser(
        description="GimKit CSV → Wayground（原 Quizizz）試算表匯入格式（.xlsx，每題含秒數）"
    )
    ap.add_argument("source", help="GimKit 格式來源 CSV（Question, Correct Answer, Incorrect 1-3）")
    ap.add_argument("-o", "--output", help="輸出 xlsx 路徑（預設: <來源檔名去掉副檔名>-wayground.xlsx）")
    ap.add_argument(
        "--time",
        default=str(DEFAULT_TIME),
        help=f"每題秒數，限 {', '.join(str(t) for t in TIME_CHOICES)}（預設: {DEFAULT_TIME}）",
    )
    args = ap.parse_args()

    if args.time not in [str(t) for t in TIME_CHOICES]:
        fail(
            f"--time 只能是 {', '.join(str(t) for t in TIME_CHOICES)}"
            f"（官方範本的時間下拉值），收到: {args.time!r}"
        )
    out_path = args.output or (args.source.rsplit(".", 1)[0] + "-wayground.xlsx")
    if not out_path.lower().endswith(".xlsx"):
        fail(f"輸出必須是 .xlsx（Wayground 匯入用自己的試算表範本），收到: {out_path!r}")

    data = read_source(args.source)
    time_limit = int(args.time)
    rows = convert(data, time_limit)
    write_xlsx(rows, time_limit, out_path)
    verify(out_path, data, time_limit)
    print(f"完成: {len(rows)} 題 → {out_path}")


if __name__ == "__main__":
    main()
