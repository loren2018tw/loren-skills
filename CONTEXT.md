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

**群組示意圖**（grouped diagram）:
Word 文件中以群組構成的示意圖，一張底圖疊上多個帶座標的文字方塊；底圖與文字方塊在檔案結構上是分開的。
_Avoid_: 組合圖、圖組、示意圖群組

**圖內文字**（in-image text）:
群組示意圖中由文字方塊承載、不屬於底圖像素內容的文字。
_Avoid_: 圖說、方塊字、圖中字

**標注圖**（annotated image）:
已把圖內文字繪回底圖原位置的媒體資產，也就是 md 實際引用的圖檔。
_Avoid_: 疊字圖、合成圖、annotated 圖

### GimKit 選擇題出題

**核心概念**（key concept）:
文本中值得反覆提問的學習目標，選擇題的正解單位。
_Avoid_: 重要概念、考點

**一答多問**（one-answer-many-questions）:
同一核心概念以多個不同情境或角度的題幹反覆提問，每題正解皆為該概念本身。
_Avoid_: 多面向

**概念屬性題**（property question）:
正解為文本明述、關於核心概念的敘述句——屬性、成因、機制、年代、數值或人物事實——而非概念詞本身的題型。
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

### GimKit 轉 Blooket

**匯入範本**（import template）:
Blooket 官方提供的 CSV 上傳格式，前兩列（標題列＋欄名列）會被前端解析跳過。
_Avoid_: 範本檔、官方格式

**正解位置**（correct answer position）:
Blooket 第 8 欄 Correct Answer(s) 填的數字 1~4，指正解落在 Answer 1~4 的哪一格，不是答案文字。
_Avoid_: 答案編號、正解欄

**正解位置輪替**（position rotation）:
逐題把正解依 1→2→3→4 順序放進不同的 Answer 欄位，避免正解集中在同一位置。
_Avoid_: 隨機打散、洗牌

**匯入前驗證**（pre-import verification）:
輸出前模擬 Blooket 前端解析流程（跳過前兩列 → 過濾 → 取前 10 欄）逐題比對來源的檢查。
_Avoid_: 自我檢查、測試

### 技能安裝

**技能目錄**（skill directory）:
根目錄下含 SKILL.md 的一級目錄，是安裝的最小單位。
_Avoid_: 技能資料夾、skill folder

**目標技能庫**（target skills directory）:
agent 掃描技能的位置，預設 ~/.agents/skills。
_Avoid_: 安裝目錄、skills 資料夾

**連結安裝**（link install）:
在目標技能庫建立指向技能目錄的檔案系統連結（Unix symlink／Windows junction），技能內容更新即時生效。
_Avoid_: 軟連結安裝、symlink 安裝、複製安裝

**外部技能**（external skill）:
由其他工具（vercel skills CLI）以複本安裝、非本 repo 管理的技能。
_Avoid_: 第三方技能
