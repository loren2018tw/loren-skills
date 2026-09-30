# Blooket CSV format

Blooket imports question sets from a CSV uploaded via
Create → CSV Import → Create Your Set → Upload CSV. The import template
has eight columns; produce files matching it. The source is a GimKit
export with five columns: `Question, Correct Answer, Incorrect Answer 1,
Incorrect Answer 2, Incorrect Answer 3` — its row rules are the same
contract the `create-gimkit-questions` skill writes to.

```
Question #,Question Text,Answer 1,Answer 2,Answer 3,Answer 4,Time Limit (sec),Correct Answer(s)
```

The rules below were verified against the Blooket official template and the
dashboard.blooket.com front-end bundle (2026-09); do not re-derive them each run.

## Field mapping (GimKit → Blooket)

| GimKit source column | Blooket output column |
|---|---|
| Question | Question Text（第 2 欄，索引 1） |
| Correct Answer | 放入 Answer 1~4，位置**輪替打散**（1→2→3→4） |
| Incorrect Answer 1~3 | 填入其餘選項欄 |
| —（無） | Time Limit (sec)（第 7 欄，預設 30） |
| —（無） | Correct Answer(s)（第 8 欄）= 正解所在**位置數字** 1~4，不是答案文字 |

## Parsing rules the front-end applies

1. **前兩列表頭不可省** — Blooket 前端用 Papa.parse 讀檔後 `slice(2)` 跳過前兩列
   （標題列 "Blooket\nImport Template" ＋ 欄名列）。只留一列表頭會讓第一題被當表頭吃掉。
2. **資料列篩選條件** — 保留「≥ 8 欄且第 2 欄非空」的列，並只取前 10 欄。
   每欄順序固定: Question # / Question Text / Answer 1-4 / Time Limit / Correct Answer(s)。
3. **正解位置必須主動輪替** — 來源正解固定在第一欄，且 CSV 匯入**不會**自動啟用
   「隨機答案順序」（那是要在題目編輯器另外設定的選項）。照抄會讓學生發現
   「選項 1 永遠是答案」，因此腳本固定以 1→2→3→4 輪替正解位置。

## File details

- Encoding: UTF-8 **with BOM**（Excel 直接開啟檢查中文不亂碼，Papa.parse 會自動去除）。
- Line endings: CRLF。
- Time Limit: 上限 300 秒，範本欄名註明 `(Max: 300 seconds)`。

## Verification gate

腳本在輸出前模擬 Blooket 前端解析（跳過前兩列 → 過濾 ≥ 8 欄且第 2 欄非空 → 取前 10 欄），
逐題比對:

- 題目文字與來源一致；
- 選項集合與來源一致；
- 正解位置數字指向的選項確實是來源正解；
- 每題 Time Limit 與參數一致；
- 正解位置分布接近 25/25/25/25（尾數略少可接受，如 19/19/19/18）。

全部通過才交出檔案；失敗時腳本 exit 1 並列出問題，修正後重跑，不要手工修補輸出 CSV。
