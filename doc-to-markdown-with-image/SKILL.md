---
name: doc-to-markdown-with-image
description: Convert Word documents (.docx or legacy .doc) to clean markdown while extracting embedded images as real files (media assets) referenced by relative paths, drawing text from grouped text boxes (concept diagrams) back onto the extracted images and keeping that text in the markdown for agents (pandoc loses it). Use when the user asks to convert a Word document to markdown or md and keep the images, or asks for a markitdown-style conversion that preserves images. Do not use for PDF, PPTX, EPUB, HTML, or non-Word sources.
---

# doc-to-markdown-with-image

把 Word 文件（來源文件）轉成簡潔 markdown，並把內嵌圖片抽出成實體圖檔（媒體資產），md 以相對路徑引用。群組示意圖的圖內文字會依原位置繪回底圖（覆蓋原檔、一律 PNG），讓圖直接看得懂；同一批文字仍保留在圖下，作為 agent 的可靠來源。轉換引擎是 markitdown（mammoth），圖檔由合併腳本從 docx 還原，標注由 `annotate_images.py` 負責。

選 markitdown 而非 pandoc 的原因：課本、報告常把示意圖文字放在「群組文字方塊」裡（`w:txbxContent`），pandoc 的 docx reader 對群組內文字全數流失；markitdown 一份不漏。

## 啟動條件

- 使用者要求把 .docx / .doc 轉成 markdown 且要保留圖片時觸發；使用者也可直接以 skill 名稱啟動。
- 來源不是 Word 文件（PDF、PPTX 等）時，告知本 skill 不支援，不要動手。
- 環境需求：Python 3.8+、`markitdown`（0.1.8+，`uv tool install 'markitdown[docx]'`）、`Pillow`（圖內文字標注，本技能必要依賴：`python3 -m pip install pillow`，Windows 用 `py -3 -m pip install pillow`；純標準庫政策的例外，見 `docs/adr/0005`）、`soffice`（LibreOffice，僅 `.doc` 橋接與 emf/wmf 轉檔需要）。缺任一者即回報安裝指令，不要臨場改用別的工具改寫輸出風格。

## 工作流程

1. 執行轉換腳本（路徑相對本 skill 目錄）：
   | 平台 | 指令 |
   | --- | --- |
   | Windows | `py -3 scripts/doc-to-md.py <來源文件> [輸出資料夾]` |
   | macOS / Linux | `python3 scripts/doc-to-md.py <來源文件> [輸出資料夾]` |
   表中指令不存在時，Windows 改試 `python`、macOS/Linux 改試 `python`；都沒有就回報 Python 安裝指引（python.org 安裝器預設提供 `py` launcher），不要臨場改寫管線。
   不給輸出資料夾時，預設在來源文件同層建立同名資料夾：`<stem>.md` + `assets/`。
2. 驗收，全數成立才算完成：
   - 輸出資料夾內有 `<stem>.md`；
   - `assets/` 內有已改名的 `<stem>-image-K.<ext>` 圖檔，且 md 中引用的路徑檔案實際存在（不得有佔位連結）；
   - 群組示意圖的圖內文字已繪回底圖（該圖為標注後的 `.png`）；若出現「找不到可用的 CJK 字型」警告則允許跳過標注，但回報時須說明並提示可用 `DOC2MD_FONT` 指定字型；
   - md 內沒有 `data:image` 佔位符殘留；
   - 腳本有印「佔位符數與引用數不一致」警告（exit 2）時，未處理完不得回報完成——需人工檢查對位或改用備援管線並告知使用者。
3. 回報使用者：輸出位置與抽出的圖檔數量。

## 選用後續

使用者需要圖片的文字描述（而非只是圖檔）時，改呼叫 `image-vision-sidecar` skill 產生描述，再把結果回填各張圖的 alt 文字。此步驟不在本 skill 的必要流程內。

## 風格規範（後製的具體定義）

- 圖片一律 `![alt](<assets/<stem>-image-K.ext>)`：alt 用語意化檔名，路徑以 `<>` 包裹以容納含括號／空白的檔名。
- 相鄰佔位符（`![](...)![](...)`）先拆行再替換，不留同段雙圖。
- 不做 `{width= height=}` 清理：markitdown 輸出沒有這種屬性尾巴。

## 已知限制

- 標注是近似還原：位置、字級、顏色、對齊、直排盡量貼近 Word 版面，不追求精確換行；內容照 Word 行為溢出方塊可見，不裁切。
- 圖下文字不因標注而移除：同批文字仍完整輸出（agent 的可靠來源），與圖上文字並存。
- 無法標注的情形：群組無底圖／多張底圖、群組外的獨立文字方塊、旋轉角度非 90 度倍數、找不到 CJK 字型（可用 `DOC2MD_FONT`／`DOC2MD_FONT_BOLD` 指定字型檔，TTC 可用 `#索引`，如 `x.ttc#3`）；這些文字仍完整留在圖下。
- 標注直接覆蓋抽取出的圖檔（一律 PNG、不留原檔）；需要乾淨底圖時重新轉換來源文件即可。
- mammoth 對不認得的樣式（如課本自訂標題）輸出粗體而非 `#` 標題；需要時用 regex 後製依「1-1／一 二 三」等編號規則升級。
- `.emf/.wmf` 向量圖自動以 soffice 轉成高解析 png（1600×2200 內），md 引用指向 png（有圖內文字時同樣標注該 png），原向量檔保留在 assets 備查；soffice 缺席或轉換失敗時警告並保留原格式引用。
- 舊版 `.doc` 不支援 markitdown 直接轉換，腳本內已做 soffice 橋接。
- 佔位符格式 `data:image/...;base64...` 與 mammoth 版本綁定；markitdown 升級後若驗收屢屢失敗，優先懷疑佔位符格式改變。
