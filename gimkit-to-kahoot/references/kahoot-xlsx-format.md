# Kahoot xlsx format

Kahoot imports questions from a spreadsheet via Create → Add → Import →
Import spreadsheet. The upload is an **`.xlsx` file (MS Excel 2007 or newer)**;
there is no CSV import path — the official article says *"Save the template as a
.xlsx file"* and the template itself says *"if you're not using Excel you need
to export to .xlsx format before you upload to Kahoot"*. Only standard Quiz
questions can be imported; the template has no Type column.

The source is a GimKit export with five columns: `Question, Correct Answer,
Incorrect Answer 1, Incorrect Answer 2, Incorrect Answer 3` — its row rules are
the same contract the `create-gimkit-questions` skill writes to.

The geometry, headers and limits below were verified against the official
template download and support articles (2026-10); do not re-derive them each run.

## Template geometry

| Position | Content |
|---|---|
| Rows 1~7 | Official template's instruction text; left empty by this tool |
| Row 8 | Header: B=`Question - 120 max length`, C~F=`Answer n - 75 max length`, G=`Time limit`, H=`Correct answer(s)` |
| Row 9 onwards | One question per row: A=序號, B=題目, C~F=Answer 1~4, G=秒數, H=正解欄號 |
| Column A | Sequence number (the importer does not read it; the official template numbers 1~200) |

## Field mapping (GimKit → Kahoot)

| GimKit source column | Kahoot output column |
|---|---|
| Question | B（第 8 列為表頭，題目在第 2 欄，題目 ≤120 字） |
| Correct Answer | 放入 Answer 1~4（C~F 欄），位置**輪替打散**（1→2→3→4） |
| Incorrect Answer 1~3 | 填入其餘選項欄 |
| —（無） | G 欄 Time limit（預設 20 秒） |
| —（無） | H 欄 Correct answer(s) = 正解所在**欄號** 1~4，不是答案文字 |

## Rules the importer applies

1. **只吃 `.xlsx`** — CSV 必須先用 Excel／LibreOffice 另存成 xlsx 才上傳得動。
2. **只匯入標準 Quiz** — 題型（True/False、Poll、Puzzle…）無法由試算表指定，
   匯入後再於編輯器調整；多選題以逗號分隔正解欄號（如 `1,3`）。
3. **表頭固定第 8 列、資料自第 9 列起** — 三版官方模板（2018／2019／現行）
   幾何一致；範例列在 xlsx 第 9 列，必須被真實題目覆蓋。
4. **空白答案欄不顯示** — 每題至少 2 個答案；本工具一律填滿 4 個。
5. **匯入時系統自動檢查錯誤** — 有問題的題目會被標示，可選擇丟棄該題後繼續。

## Limits

- 題目 ≤ **120 字元**、單一選項 ≤ **75 字元**（含空白；Excel 的 `LEN()` 對中文
  每字算 1）——官方模板以資料驗證公式 `len(B9)<121`、`len(C9)<76` 鎖住。
- Time limit：官方文件列 **5/10/20/30/60/120**；無法辨識的值會被系統自動改成
  **20 秒**。模板下拉另有 15/45/90/180/240，但文章未列、伺服器是否接受未證實，
  本工具不接受。
- 題數：單一 kahoot 上限 **200 題**；超過時腳本直接失敗（exit 1），請拆檔。
- 檔案大小：官方 2018 部落格提到 ≤1MB；本工具產物約每題 0.2KB，實務上碰不到。
- 編碼：xlsx 內部是 UTF-8 XML（無 BOM），中文直接寫入即可，沒有 CSV 的編碼風險；
  本工具以 `inlineStr` 寫字串、不產生 sharedStrings 表。

## Why xlsx, not CSV

Kahoot 沒有 CSV 匯入管道（官方說明中心搜不到任何 CSV 匯入文章；網路上的
「Kahoot CSV」說法全出自第三方）。若先產 CSV 再叫使用者手動另存 xlsx，
只是把不可匯入的檔案丟給人；因此本技能直接產 `.xlsx`，以標準庫 `zipfile` +
XML 手寫最小工作簿，維持純標準庫政策（見 `docs/adr/0006`）。

## Verification gate

腳本輸出後**重讀自己寫出的 xlsx**，比對：

- 檔內列號恰為「表頭第 8 列 + 第 9 列起每題一列」；
- 第 8 列表頭逐字與官方模板一致；
- 每題的題目文字、四個選項集合與來源一致；
- H 欄欄號指向的選項確實是來源正解；
- 每題 G 欄 Time limit 與參數一致；
- 正解欄號分布接近 25/25/25/25（尾數略少可接受，如 19/19/19/18）。

全部通過才交出檔案；失敗時腳本 exit 1 並列出問題，修正後重跑，不要手工修補輸出檔。
字數超限不在此關卡內：只印警告、不修改內容、照樣輸出（Kahoot 匯入介面會標示）。
