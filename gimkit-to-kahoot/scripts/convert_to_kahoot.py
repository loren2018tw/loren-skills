#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GimKit CSV → Kahoot 試算表匯入格式（.xlsx）轉換器。

來源格式（GimKit 匯出，5 欄）:
    Question, Correct Answer, Incorrect Answer 1, Incorrect Answer 2, Incorrect Answer 3

輸出格式（複刻 Kahoot 官方匯入範本幾何，單一工作表 Sheet1）:
    第 8 列 = 表頭: B=Question, C~F=Answer 1~4, G=Time limit, H=Correct answer(s)
    第 9 列起 = 資料: A=流水號, B=題目, C~F=選項, G=秒數, H=正解欄號 1~4

Kahoot 只收 .xlsx（官方文件: Save the template as a .xlsx file (MS Excel 2007 or
newer)），沒有 CSV 匯入管道；本腳本以標準庫 zipfile + XML 直接寫出 xlsx
（不依賴 openpyxl，見 docs/adr/0006）。

用法:
    Windows:      py -3 scripts/convert_to_kahoot.py 來源GimKit.csv [-o 輸出檔.xlsx] [--time 20]
    macOS/Linux:  python3 scripts/convert_to_kahoot.py 來源GimKit.csv [-o 輸出檔.xlsx] [--time 20]
"""
import argparse
import collections
import csv
import sys
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

HEADER_ROW = 8  # 官方模板: 表頭在第 8 列（前 7 列為模板說明，本工具留空）
FIRST_DATA_ROW = 9  # 官方模板: 資料自第 9 列起

KAHOOT_MAX_QUESTIONS = 200  # 單一 kahoot 題數上限
KAHOOT_MAX_QUESTION_CHARS = 120  # 官方模板表頭註明 "Question - 120 max length"
KAHOOT_MAX_ANSWER_CHARS = 75  # 官方模板表頭註明 "Answer n - 75 max length"
# 官方文件的守恆時間值（文章: 5, 10, 20, 30, 60, or 120）；模板下拉另有
# 15/45/90/180/240，文章未列、伺服器是否接受未證實，故不接受。
KAHOOT_TIME_CHOICES = (5, 10, 20, 30, 60, 120)
KAHOOT_DEFAULT_TIME = 20  # 匯入值無效時 Kahoot 會自動改成 20 秒

HEADER_CELLS = [
    "Question - 120 max length",
    "Answer 1 - 75 max length",
    "Answer 2 - 75 max length",
    "Answer 3 - 75 max length",
    "Answer 4 - 75 max length",
    "Time limit",
    "Correct answer(s)",
]

_CONTENT_TYPES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

_WORKBOOK = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

_WORKBOOK_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
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
    """1-based 欄序 → Excel 欄名（1=A, 2=B, …）。本工具只用到 A~H。"""
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
    if len(data) > KAHOOT_MAX_QUESTIONS:
        fail(
            f"來源共 {len(data)} 題，超過 Kahoot 單一 kahoot 上限 "
            f"{KAHOOT_MAX_QUESTIONS} 題；請拆成多份來源檔再轉換"
        )
    return data


def convert(data: list[list[str]], time_limit: int) -> list[tuple[str, list[str], int]]:
    """正解位置輪替 1→2→3→4，回傳每題 (題目, 四選項, 正解欄號)。"""
    out_rows = []
    for i, r in enumerate(data, start=1):
        question, correct = r[0].strip(), r[1].strip()
        others = [c.strip() for c in r[2:5]]
        # 來源正解固定在第 2 欄；照抄會讓正解永遠落在 Answer 1，
        # 因此主動輪替，讓教師在 Kahoot 編輯器檢查時看到正解分散。
        pos = (i - 1) % 4 + 1
        answers = others[: pos - 1] + [correct] + others[pos - 1 :]
        out_rows.append((question, answers, pos))
    return out_rows


def check_limits(data: list[list[str]]) -> list[str]:
    """列出超過 Kahoot 字數限制的題目（警告，不修改內容、不中止）。"""
    warns = []
    for i, r in enumerate(data, start=1):
        question = r[0].strip()
        if len(question) > KAHOOT_MAX_QUESTION_CHARS:
            warns.append(
                f"  第 {i} 題: 題目 {len(question)} 字（上限 {KAHOOT_MAX_QUESTION_CHARS}）"
            )
        for j, option in enumerate(r[1:5], start=1):
            text = option.strip()
            if len(text) > KAHOOT_MAX_ANSWER_CHARS:
                warns.append(
                    f"  第 {i} 題: 選項 {j} {len(text)} 字（上限 {KAHOOT_MAX_ANSWER_CHARS}）"
                )
    return warns


def _clean(text: str) -> str:
    """移除 XML 不允許的控制字元（保留 tab 與換行），再跳脫 & < >。"""
    kept = [c for c in text if c in "\t\n" or c >= " "]
    return escape("".join(kept))


def _cell(ref: str, value: object, numeric: bool = False) -> str:
    if numeric:
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{_clean(str(value))}</t></is></c>'


def _sheet_xml(rows: list[tuple[str, list[str], int]], time_limit: int) -> str:
    """組出 sheet1.xml：表頭在第 8 列、資料自第 9 列起（比照官方模板）。"""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{NS_MAIN}"><sheetData>',
    ]
    cells = [_cell(f"{col_letter(2 + k)}{HEADER_ROW}", text) for k, text in enumerate(HEADER_CELLS)]
    # A 欄依官方模板留空（模板的流水號在 A 欄資料列，不在表頭列）
    parts.append(f'<row r="{HEADER_ROW}">{"".join(cells)}</row>')
    for i, (question, answers, pos) in enumerate(rows, start=1):
        r = FIRST_DATA_ROW + i - 1
        row = [_cell(f"A{r}", i, numeric=True), _cell(f"B{r}", question)]
        row += [_cell(f"{col_letter(3 + k)}{r}", text) for k, text in enumerate(answers)]
        row += [
            _cell(f"G{r}", time_limit, numeric=True),
            _cell(f"H{r}", pos, numeric=True),
        ]
        parts.append(f'<row r="{r}">{"".join(row)}</row>')
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def write_xlsx(rows: list[tuple[str, list[str], int]], time_limit: int, path: str) -> None:
    """以標準庫寫出最小 xlsx（無樣式、字串用 inlineStr，不需 sharedStrings）。"""
    parts = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _ROOT_RELS,
        "xl/workbook.xml": _WORKBOOK,
        "xl/_rels/workbook.xml.rels": _WORKBOOK_RELS,
        "xl/worksheets/sheet1.xml": _sheet_xml(rows, time_limit),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, _ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, text.encode("utf-8"))


def read_xlsx(path: str) -> dict[int, dict[str, str]]:
    """重讀產出的 xlsx，回傳 {列號: {欄名: 值}}（驗證用）。"""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
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
    return table


def verify(path: str, src: list[list[str]], time_limit: int) -> None:
    """重讀產出的 xlsx，比對表頭列位與逐題內容（題目、選項集合、正解欄號、時間）。"""
    table = read_xlsx(path)
    errs = []
    expected_rows = [HEADER_ROW] + list(range(FIRST_DATA_ROW, FIRST_DATA_ROW + len(src)))
    if sorted(table) != expected_rows:
        fail(f"驗證失敗: 產出檔列號 {sorted(table)} ≠ 預期 {expected_rows}")
    if table[HEADER_ROW] != {col_letter(2 + k): t for k, t in enumerate(HEADER_CELLS)}:
        errs.append(f"表頭（第 {HEADER_ROW} 列）與官方範本不符: {table[HEADER_ROW]}")
    pos_dist = collections.Counter()
    for i, s in enumerate(src, start=1):
        cells = table[FIRST_DATA_ROW + i - 1]
        question, correct = s[0].strip(), s[1].strip()
        answers = [cells.get(col_letter(3 + k), "") for k in range(4)]
        pos_text = cells.get("H", "")
        if cells.get("A") != str(i):
            errs.append(f"第 {i} 題: A 欄流水號 = {cells.get('A')!r}")
        if cells.get("B") != question:
            errs.append(f"第 {i} 題: 題目文字不符")
        if cells.get("G") != str(time_limit):
            errs.append(f"第 {i} 題: Time limit = {cells.get('G')!r}（應為 {time_limit}）")
        if pos_text not in ("1", "2", "3", "4"):
            errs.append(f"第 {i} 題: Correct answer(s) = {pos_text!r}")
            continue
        pos = int(pos_text)
        pos_dist[pos] += 1
        if answers[pos - 1] != correct:
            errs.append(f"第 {i} 題: 欄號 {pos} 的選項不是正解")
        if sorted(answers) != sorted(x.strip() for x in s[1:5]):
            errs.append(f"第 {i} 題: 選項集合與來源不符")
    if errs:
        fail("驗證失敗:\n" + "\n".join(errs))
    print("驗證: ✅ 重讀產出檔（xlsx）逐題比對通過，與來源一致")
    print(f"驗證: 正解欄號分布 = {dict(sorted(pos_dist.items()))}")
    print(f"驗證: Time limit 全為 {time_limit} 秒")


def main() -> None:
    use_utf8_stdio()
    ap = argparse.ArgumentParser(
        description="GimKit CSV → Kahoot 試算表匯入格式（.xlsx，每題含 Time limit）"
    )
    ap.add_argument("source", help="GimKit 格式來源 CSV（Question, Correct Answer, Incorrect 1-3）")
    ap.add_argument("-o", "--output", help="輸出 xlsx 路徑（預設: <來源檔名去掉副檔名>-kahoot.xlsx）")
    ap.add_argument(
        "--time",
        default=str(KAHOOT_DEFAULT_TIME),
        help=f"每題秒數，限 {', '.join(str(t) for t in KAHOOT_TIME_CHOICES)}（預設: {KAHOOT_DEFAULT_TIME}）",
    )
    args = ap.parse_args()

    if args.time not in [str(t) for t in KAHOOT_TIME_CHOICES]:
        fail(
            f"--time 只能是 {', '.join(str(t) for t in KAHOOT_TIME_CHOICES)}"
            f"（Kahoot 官方文件列出的時間值），收到: {args.time!r}"
        )
    out_path = args.output or (args.source.rsplit(".", 1)[0] + "-kahoot.xlsx")
    if not out_path.lower().endswith(".xlsx"):
        fail(f"輸出必須是 .xlsx（Kahoot 只接受 .xlsx 匯入），收到: {out_path!r}")

    data = read_source(args.source)
    time_limit = int(args.time)
    warns = check_limits(data)
    if warns:
        print(
            f"⚠️ 警告: {len(warns)} 處超過 Kahoot 長度限制"
            f"（題目 ≤{KAHOOT_MAX_QUESTION_CHARS} 字、選項 ≤{KAHOOT_MAX_ANSWER_CHARS} 字）；"
            "內容不代為修改，匯入時 Kahoot 會標示這些題目:"
        )
        print("\n".join(warns))
    rows = convert(data, time_limit)
    write_xlsx(rows, time_limit, out_path)
    verify(out_path, data, time_limit)
    print(f"完成: {len(rows)} 題 → {out_path}")


if __name__ == "__main__":
    main()
