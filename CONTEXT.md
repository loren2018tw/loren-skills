# loren-skills

本 repo 是 agent skills 的集合，每個目錄是一個獨立 skill。目前此 CONTEXT.md 收錄「文件轉 Markdown」領域的共用術語。

## Language

**來源文件**（source document）:
餵給轉換流程的輸入檔案（.docx 或舊版 .doc）。
_Avoid_: 原始檔、input file

**媒體資產**（media assets）:
從來源文件抽出、存在輸出目錄 `assets/` 下的實體圖檔，md 以相對路徑引用。
_Avoid_: 圖片檔、media folder、附圖

**後製**（post-process）:
把轉換工具的原始輸出整理成標準風格的步驟（ATX 標題、去 `{width= height=}`、不換行）。
_Avoid_: 清理、修正、cleanup

**相容性橋接**（compatibility bridge）:
pandoc 讀不了舊版 .doc 時，先用 LibreOffice 把 .doc 轉成 .docx 的前置步驟。
_Avoid_: 格式轉換、格式橋接
