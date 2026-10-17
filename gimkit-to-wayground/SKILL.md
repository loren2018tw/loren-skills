---
name: gimkit-to-wayground
description: 把 GimKit 匯出的題庫 CSV（Question, Correct Answer, Incorrect 1-3）轉換為可直接上傳匯入 Wayground（原 Quizizz）的 .xlsx 試算表，依官方範本版面（表頭第 1 列、資料第 3 列起、Question Type 為 Multiple Choice）、Time in seconds（預設 30）、正解位置輪替與匯入前驗證。當使用者要「轉成 Wayground」「轉成 Quizizz」「匯入 Wayground」「GimKit 轉 Wayground」「題庫轉 Quizizz 格式」或提到要幫 Wayground（Quizizz）建題庫時載入。不要用於 Blooket、Kahoot 等其他平台格式；Wayground 沒有 CSV 匯入管道，產物固定為 .xlsx。
---

# GimKit → Wayground 轉換

將 GimKit 匯出的題庫 CSV 轉成 Wayground（原 Quizizz）試算表匯入格式（.xlsx），上傳後即可使用。

## Required context

動筆前先讀 [Wayground xlsx 格式](references/wayground-xlsx-format.md):
官方範本幾何、來源與輸出欄位對照、題型與時間的下拉值、第 2 列留空的理由、驗證標準。

領域詞彙在 repo GLOSSARY.md 的「題庫格式轉換（GimKit 匯出）」一節:
正解位置、正解位置輪替、匯入前驗證、範本列位。

## 工作流程

### 1. 執行轉換腳本（路徑相對本 skill 目錄）

| 平台 | 指令 |
| --- | --- |
| Windows | `py -3 scripts/convert_to_wayground.py 來源-gimkit.csv -o Wayground匯入_單元1選擇題.xlsx --time 30` |
| macOS / Linux | `python3 scripts/convert_to_wayground.py 來源-gimkit.csv -o Wayground匯入_單元1選擇題.xlsx --time 30` |

表中指令不存在時，Windows 改試 `python`、macOS/Linux 改試 `python`；都沒有就回報 Python 安裝指引（python.org 安裝器預設提供 `py` launcher），不要臨場改寫管線。

- `-o` 輸出路徑（預設: `<來源檔名去副檔名>-wayground.xlsx`，寫在來源檔同層）；必須是 `.xlsx`
- `--time` 每題秒數，限 5/10/20/30/45/60/120/180/300/900（範本時間下拉值），預設 30

### 2. 確認驗證輸出

腳本會自動做來源欄位檢查（恰 5 欄、無空欄、選項不重複）與匯入前驗證
（重讀寫出的 xlsx 逐題比對，含工作表名、表頭列位、題型欄與留空欄），全部通過才會輸出
檔案與完成訊息；驗證內容與失敗處理見 [Wayground xlsx 格式](references/wayground-xlsx-format.md)。
驗證失敗會列出所有問題並 exit 1 —— 修正來源或回報使用者，**不要**交出未通過驗證的檔案。

範本未標示字數或題數上限，腳本不代為設限，也不修改任何文字內容。

### 3. 告訴使用者匯入步驟

1. 登入 [Wayground](https://wayground.com)（原 Quizizz）→ **Create** → **Assessment**
2. 匯入選項選 **Import from spreadsheet**（試算表匯入）
3. 上傳產出的 `.xlsx`，於預覽畫面確認題目與題型正確後匯入
4. 匯入後可再補圖片（J 欄 Image Link）或詳解（K 欄 Answer explanation）

## 注意事項

- **來源格式** — 本腳本針對 GimKit 的 5 欄格式（正解在第 2 欄）。其他來源格式先確認
  欄位結構再使用；如來源不是此格式，先轉成此格式或直接修改腳本 `read_source`。
- **只支援選擇題** — 輸出題型固定 `Multiple Choice`、每題 4 個選項、單一正解；
  範本支援的其他題型（Checkbox、Fill-in-the-Blank、Poll…）不在此技能範圍。
- **列位** — 表頭第 1 列、資料第 3 列起（第 2 列是範本說明列，留空）。若上傳後發現
  題目被吃掉或位移，調 `FIRST_DATA_ROW` 常數重跑，不要在輸出檔上手改。
- **輸出後抽查** — 建議再抽查 2~3 題確認中文內容與正解欄號正確（如第 1、2 題）。
