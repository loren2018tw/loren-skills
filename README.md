# loren-skills

Loren 自製的 agent 技能收藏倉。

## 技能列表

- **who-is-loren**: 關於作者本人的基本事實（姓名、email、GitHub、興趣）。agent 需要稱呼或介紹 Loren 時使用。
- **doc-to-markdown-with-image**: 把 Word 文件（.docx／舊版 .doc 經 LibreOffice 橋接）轉成簡潔 markdown，並把內嵌圖片抽出成實體檔、以相對路徑引用。
- **textbook-analysis**: 把課本章節、講義、題目與參考答案透析成結構化知識（核心概念、概念關係、考題辨識、解題邏輯、易錯陷阱、一分鐘背誦版），輸出為與原始文本分離的獨立 markdown 檔。

## 如何讓技能可用

每個技能是一個目錄，內含 `SKILL.md`。將目錄複製或 symlink 到 `~/.agents/skills/<技能名>/` 即可被 agent 呼叫。

本倉庫目前只持有技能源碼，不負責自動安裝。
