---
name: gimkit-to-blooket
description: 把 GimKit 匯出的題庫 CSV（Question, Correct Answer, Incorrect 1-3）轉換為可直接上傳匯入 Blooket 遊戲學習平台的官方範本格式 CSV，含每題 Time Limit（預設 30 秒）、正解位置輪替打散與匯入前驗證。當使用者要「轉成 Blooket」「匯入 Blooket」「GimKit 轉 Blooket」「題庫轉 Blooket 格式」「quiz CSV 轉 blooket」或提到要幫 Blooket 建題庫時載入。不要用於 Kahoot、Quizizz（Wayground）等其他平台格式。
---

# GimKit → Blooket CSV 轉換

將 GimKit 匯出的題庫 CSV 轉成 Blooket 官方匯入範本格式，轉換後立即上傳 Blooket 即可使用。

## Required context

動筆前先讀 [Blooket CSV 格式](references/blooket-csv-format.md):
來源與輸出欄位對照、Blooket 前端解析規則、檔案細節與驗證標準。

領域詞彙在 repo CONTEXT.md 的「GimKit 轉 Blooket」一節:
匯入範本、正解位置、正解位置輪替、匯入前驗證。

## 工作流程

### 1. 執行轉換腳本（路徑相對本 skill 目錄）

| 平台 | 指令 |
| --- | --- |
| Windows | `py -3 scripts/convert_to_blooket.py 來源-gimkit.csv -o Blooket匯入_單元1選擇題.csv --time 30` |
| macOS / Linux | `python3 scripts/convert_to_blooket.py 來源-gimkit.csv -o Blooket匯入_單元1選擇題.csv --time 30` |

表中指令不存在時，Windows 改試 `python`、macOS/Linux 改試 `python`；都沒有就回報 Python 安裝指引（python.org 安裝器預設提供 `py` launcher），不要臨場改寫管線。

- `-o` 輸出路徑（預設: `<來源檔名去副檔名>-blooket.csv`，寫在來源檔同層）
- `--time` 每題秒數，1~300，預設 30（依使用者要求調整）

### 2. 確認驗證輸出

腳本會自動做來源欄位檢查與匯入前驗證（模擬 Blooket 前端解析），全部通過才會
輸出檔案與完成訊息；驗證內容與失敗處理見 [Blooket CSV 格式](references/blooket-csv-format.md)。
驗證失敗會列出所有問題並 exit 1 —— 修正來源或回報使用者，**不要**交出未通過驗證的檔案。

### 3. 告訴使用者匯入步驟

1. 登入 [Blooket](https://www.blooket.com) → **Create**
2. 填標題 → 建立方式選 **CSV Import** → Create Your Set
3. **Upload CSV** 選擇產出的 CSV
4. 進入 Set Edit 頁檢查後 **Save Set**

## 注意事項

- **來源格式** — 本腳本針對 GimKit 的 5 欄格式（正解在第 2 欄）。其他來源格式先確認
  欄位結構再使用；如來源不是此格式，先轉成此格式或直接修改腳本 `read_source`。
- **多次正解** — Blooket 的 Correct Answer(s) 欄支援逗號分隔多數字（如 "1,4"），
  但 GimKit 格式每題只有 1 個正解，腳本不產生多重正解。
- **輸出後抽查** — 建議再抽查 2~3 題確認中文內容與正解標記正確（如第 1、2 題）。
