---
name: doc-to-markdown-with-image
description: Convert Word documents (.docx or legacy .doc) to clean markdown while extracting embedded images as real files (media assets) referenced by relative paths. Use when the user asks to convert a Word document to markdown or md and keep the images, or asks for a markitdown-style conversion that preserves images. Do not use for PDF, PPTX, EPUB, HTML, or non-Word sources.
---

# doc-to-markdown-with-image

把 Word 文件（來源文件）轉成簡潔 markdown，並把內嵌圖片抽出成實體圖檔（媒體資產），md 以相對路徑引用。轉換引擎是 pandoc，輸出經「後製」統一風格。

## 啟動條件

- 使用者要求把 .docx / .doc 轉成 markdown 且要保留圖片時觸發；使用者也可直接以 skill 名稱啟動。
- 來源不是 Word 文件（PDF、PPTX 等）時，告知本 skill 不支援，不要動手。

## 工作流程

1. 確認環境：`pandoc --version` 可用（3.x）；來源是舊版 .doc 時另需 `soffice`（LibreOffice）。缺任一者即回報，不要臨場改用別的工具改寫輸出風格。
2. 執行轉換腳本（路徑相對本 skill 目錄）：
   ```
   bash scripts/doc-to-md.sh <來源文件> [輸出資料夾]
   ```
   不給輸出資料夾時，預設在來源文件同層建立同名資料夾：`report.md` + `assets/`。
3. 驗收，全數成立才算完成：
   - 輸出資料夾內有 `<stem>.md`；
   - 圖片存在 `assets/` 且 md 中引用的路徑檔案實際存在（不得有佔位連結）；
   - md 內沒有 `{width= height=}` 殘留、沒有空 alt 的 `![](...)`。
4. 回報使用者：輸出位置與抽出的圖檔數量。

## 選用後續

使用者需要圖片的文字描述（而非只是圖檔）時，改呼叫 `image-vision-sidecar` skill 產生描述，再把結果回填各張圖的 alt 文字。此步驟不在本 skill 的必要流程內。

## 風格規範（後製的具體定義）

- ATX 標題（`#`）。
- `--wrap=none`：單行段落不折行。
- 去除 `{width="..." height="..."}` 屬性尾巴。
- alt 空值填語意化檔名（如 `report-image-1`），不留 `![]()`。
- writer 用 `markdown-raw_html`：獨立圖片輸出為 `![alt](path)`，不是 `<figure>` HTML。
