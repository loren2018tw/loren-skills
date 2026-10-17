---
name: gimkit-to-kahoot
description: 把 GimKit 匯出的題庫 CSV（Question, Correct Answer, Incorrect 1-3）轉換為可直接上傳匯入 Kahoot 的 .xlsx 試算表，含官方模板版面（表頭第 8 列、資料第 9 列起）、Time limit（預設 20 秒）、正解位置輪替與匯入前驗證。當使用者要「轉成 Kahoot」「匯入 Kahoot」「GimKit 轉 Kahoot」「題庫轉 Kahoot 格式」「quiz CSV 轉 kahoot」或提到要幫 Kahoot 建題庫時載入。不要用於 Blooket（gimkit-to-blooket）、Wayground／Quizizz（gimkit-to-wayground）等其他平台格式；Kahoot 沒有 CSV 匯入管道，產物固定為 .xlsx。
---

# GimKit → Kahoot 轉換

將 GimKit 匯出的題庫 CSV 轉成 Kahoot 試算表匯入格式（.xlsx），上傳 Kahoot 後即可使用。

## Required context

動筆前先讀 [Kahoot xlsx 格式](references/kahoot-xlsx-format.md):
官方模板幾何、來源與輸出欄位對照、Kahoot 匯入規則、字數與題數限制、驗證標準。

領域詞彙在 repo GLOSSARY.md 的「題庫格式轉換（GimKit 匯出）」（正解位置、正解位置輪替、
匯入前驗證）與「GimKit 轉 Kahoot」（範本列位）兩節。

## 工作流程

### 1. 執行轉換腳本（路徑相對本 skill 目錄）

| 平台 | 指令 |
| --- | --- |
| Windows | `py -3 scripts/convert_to_kahoot.py 來源-gimkit.csv -o Kahoot匯入_單元1選擇題.xlsx --time 20` |
| macOS / Linux | `python3 scripts/convert_to_kahoot.py 來源-gimkit.csv -o Kahoot匯入_單元1選擇題.xlsx --time 20` |

表中指令不存在時，Windows 改試 `python`、macOS/Linux 改試 `python`；都沒有就回報 Python 安裝指引（python.org 安裝器預設提供 `py` launcher），不要臨場改寫管線。

- `-o` 輸出路徑（預設: `<來源檔名去副檔名>-kahoot.xlsx`，寫在來源檔同層）；必須是 `.xlsx`
- `--time` 每題秒數，限 5/10/20/30/60/120（Kahoot 官方文件列出的值），預設 20

### 2. 確認驗證輸出

腳本會自動做來源欄位檢查（恰 5 欄、無空欄、選項不重複、≤200 題）與匯入前驗證
（重讀寫出的 xlsx 逐題比對），全部通過才會輸出檔案與完成訊息；驗證內容與失敗處理見
[Kahoot xlsx 格式](references/kahoot-xlsx-format.md)。
驗證失敗會列出所有問題並 exit 1 —— 修正來源或回報使用者，**不要**交出未通過驗證的檔案。

題目超過 120 字或選項超過 75 字時只印警告（不修改內容、照常輸出），把題號清單轉告使用者，
讓他在 Kahoot 匯入介面處理被標示的題目。

### 3. 告訴使用者匯入步驟

1. 登入 [Kahoot](https://kahoot.com) → **Create** → **Add** → **Import** → **Import spreadsheet**
2. 拖入或 **Select File** 選擇產出的 `.xlsx` → **Upload**
3. Kahoot 會自動檢查錯誤；若有題目被標示，依畫面指示修正或丟棄該題
4. 匯入後可再補圖片、影片或調整題型（試算表只支援標準 Quiz）

## 注意事項

- **來源格式** — 本腳本針對 GimKit 的 5 欄格式（正解在第 2 欄）。其他來源格式先確認
  欄位結構再使用；如來源不是此格式，先轉成此格式或直接修改腳本 `read_source`。
- **只支援選擇題** — 試算表匯入只能產生標準 Quiz；本腳本每題固定 4 個選項、單一正解。
- **Kahoot 沒有 CSV 匯入** — 產物固定 `.xlsx`（腳本會擋下非 `.xlsx` 的輸出路徑）。
  使用者若要求 CSV，說明此限制後照常產出 xlsx。
- **輸出後抽查** — 建議再抽查 2~3 題確認中文內容與正解欄號正確（如第 1、2 題）。
