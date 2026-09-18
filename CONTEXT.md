# loren-skills

本 repo 是 agent skills 的集合，每個目錄是一個獨立 skill。此 CONTEXT.md 按技能分組收錄各領域的共用術語。

## Language

### 文件轉 Markdown

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

### GimKit 選擇題出題

**核心概念**（key concept）:
文本中值得反覆提問的學習目標，選擇題的正解單位。
_Avoid_: 重要概念、考點

**一答多問**（one-answer-many-questions）:
同一核心概念以多個不同情境或角度的題幹反覆提問，每題正解皆為該概念本身。
_Avoid_: 多面向

**概念屬性題**（property question）:
正解為核心概念的屬性、成因或機制敘述，而非概念詞本身的題型。
_Avoid_: 因果題、機制題

**混合式產題**（mixed question generation）:
一份 kit 可含一答多問題、概念屬性題與字詞題，依文本素材自動配比。
_Avoid_: 混合模式、雙軌出題

**干擾選項**（distractor）:
選擇題中錯誤但看似合理的選項，須與正解相關或為易混概念。
_Avoid_: 錯誤選項、垃圾選項、誘答選項

**關鍵字詞**（key word）:
文本中值得考其音讀或意義的字詞。
_Avoid_: 生難詞、名詞定義

**字詞題**（word question）:
引錄原文含目標詞的句子，考該詞音讀或意義的題型。
_Avoid_: 字音字形題、釋義題
