#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GimKit CSV → Blooket 官方匯入範本格式轉換器。

來源格式（GimKit 匯出，5 欄）:
    Question, Correct Answer, Incorrect Answer 1, Incorrect Answer 2, Incorrect Answer 3

輸出格式（Blooket 官方匯入範本，8 欄）:
    Question #, Question Text, Answer 1~4, Time Limit (sec), Correct Answer(s)

Blooket 前端解析規則（取自 dashboard.blooket.com bundle 程式碼，2026-09 驗證）:
  - Papa.parse（逗號分隔）讀檔 → slice(2) 跳過前兩列（範本標題列 + 欄名列）
  - 保留「至少 8 欄且第 2 欄（Question Text，索引 1）非空」的資料列
  - 每列欄位: 0=Question #、1=Question Text、2~5=Answer 1~4、
              6=Time Limit (sec)、7=Correct Answer(s)（位置數字 1-4，多解以逗號分隔）

用法:
    python3 scripts/convert_to_blooket.py 來源GimKit.csv [-o 輸出檔.csv] [--time 30]
"""
import argparse
import collections
import csv
import sys

BLOOKET_MAX_TIME = 300  # Blooket 範本欄名註明 (Max: 300 seconds)


def fail(msg: str) -> None:
    sys.stdout.flush()
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def read_source(path: str) -> list[list[str]]:
    """讀取 GimKit 來源 CSV，驗證欄數與空欄，回傳資料列（不含表頭）。"""
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
        if len(r) < 3:
            problems.append(f"  第 {i} 題只有 {len(r)} 欄（至少需: 題目+正解+1個錯誤選項）")
            continue
        if len(r) > 5:
            problems.append(f"  第 {i} 題有 {len(r)} 欄（預期 5 欄，請確認來源格式）")
        for col, label in enumerate(r):
            if not label.strip():
                problems.append(f"  第 {i} 題第 {col + 1} 欄為空")
    if problems:
        fail("來源檔欄位檢查未通過:\n" + "\n".join(problems))
    return data


def convert(data: list[list[str]], time_limit: str) -> list[list[str]]:
    """正解位置輪替 1→2→3→4，產生 Blooket 資料列。"""
    out_rows = []
    for i, r in enumerate(data, start=1):
        q, correct = r[0].strip(), r[1].strip()
        distractors = [c.strip() for c in r[2:5]]
        # 來源正解固定在第一欄；Blooket CSV 匯入不會自動啟用「隨機答案順序」，
        # 照抄會讓正解永遠出現在選項 1，因此主動輪替打散位置。
        pos = (i - 1) % 4 + 1
        answers, it = [], iter(distractors)
        for p in range(1, 5):
            answers.append(correct if p == pos else next(it))
        assert answers[pos - 1] == correct and len(set(answers)) == 4
        out_rows.append([str(i), q, *answers, time_limit, str(pos)])
    return out_rows


def write_blooket_csv(out_rows: list[list[str]], path: str) -> None:
    """依 Blooket 官方範本寫出：前兩列表頭（前端會跳過）+ 資料列。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM 讓 Excel 開啟中文不亂碼
        w = csv.writer(f, lineterminator="\r\n")
        # 列 1: 官方範本標題列
        w.writerow(["Blooket\nImport Template"] + [""] * 7)
        # 列 2: 官方範本欄名（文字含換行，以引號包住）
        w.writerow(
            [
                "Question #",
                "Question Text",
                "Answer 1",
                "Answer 2",
                "Answer 3\n(Optional)",
                "Answer 4\n(Optional)",
                f"Time Limit (sec)\n(Max: {BLOOKET_MAX_TIME} seconds)",
                "Correct Answer(s)\n(Only include Answer #)",
            ]
        )
        w.writerows(out_rows)


def verify(src: list[list[str]], out_rows: list[list[str]], time_limit: str) -> None:
    """模擬 Blooket 前端解析流程，逐題比對來源與輸出。"""
    # 前端: slice(2) → 過濾(≥8欄且第2欄非空) → 取前10欄
    parsed = [m[:10] for m in out_rows if len(m) >= 8 and m[1] != ""]
    if len(parsed) != len(src):
        fail(f"驗證失敗: 輸出 {len(parsed)} 題 ≠ 來源 {len(src)} 題")
    errs = []
    pos_dist = collections.Counter()
    for i, (m, s) in enumerate(zip(parsed, src), start=1):
        answers, pos = m[2:6], m[7]
        if m[0] != str(i):
            errs.append(f"第 {i} 題: Question # = {m[0]!r}")
        if m[1] != s[0].strip():
            errs.append(f"第 {i} 題: 題目文字不符")
        if m[6] != time_limit:
            errs.append(f"第 {i} 題: Time Limit = {m[6]!r}（應為 {time_limit}）")
        if pos not in ("1", "2", "3", "4"):
            errs.append(f"第 {i} 題: Correct Answer(s) = {pos!r}")
            continue
        pos = int(pos)
        pos_dist[pos] += 1
        if answers[pos - 1] != s[1].strip():
            errs.append(f"第 {i} 題: 位置 {pos} 的選項不是正解")
        if sorted(answers) != sorted(x.strip() for x in s[1:5]):
            errs.append(f"第 {i} 題: 選項集合與來源不符")
    if errs:
        fail("驗證失敗:\n" + "\n".join(errs))
    print("驗證: ✅ 模擬 Blooket 前端解析通過，逐題與來源一致")
    print(f"驗證: 正解位置分布 = {dict(sorted(pos_dist.items()))}")
    print(f"驗證: Time Limit 全為 {time_limit} 秒")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="GimKit CSV → Blooket 官方匯入範本格式（每題含 Time Limit）"
    )
    ap.add_argument("source", help="GimKit 格式來源 CSV（Question, Correct Answer, Incorrect 1-3）")
    ap.add_argument("-o", "--output", help="輸出 CSV 路徑（預設: <來源檔名去掉副檔名>-blooket.csv）")
    ap.add_argument(
        "--time", default="30", help="每題秒數，1~300（預設: 30）"
    )
    args = ap.parse_args()

    if not args.time.isdigit() or not (1 <= int(args.time) <= BLOOKET_MAX_TIME):
        fail(f"--time 必須是 1~{BLOOKET_MAX_TIME} 的整數，收到: {args.time!r}")
    out_path = args.output or (args.source.rsplit(".", 1)[0] + "-blooket.csv")

    data = read_source(args.source)
    out_rows = convert(data, args.time)
    write_blooket_csv(out_rows, out_path)
    verify(data, out_rows, args.time)
    print(f"完成: {len(out_rows)} 題 → {out_path}")


if __name__ == "__main__":
    main()
