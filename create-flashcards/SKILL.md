---
name: create-flashcards
description: 使用 Flashcards 外掛程式 v2 語法，在 Obsidian 筆記中建立或改進有效的 Anki 快閃卡(閃卡)。適用於使用者要求將筆記、文件或學習資料轉換為卡片、修改效果不佳的卡片，或是選擇正確的受支援卡片類型時。請勿用於直接編輯 Anki 筆記，或用於無快閃卡輸出的通用摘要。
---

# 建立 Obsidian 快閃卡

根據使用者的來源資料，建立一小組實用的檢索提示 (Retrieval Prompts)。請保持來源內容的準確性、完整保留原意，並僅使用本儲存庫支援的語法。

## 必要背景知識

在建立或修改卡片之前，請先閱讀
[卡片設計 (card design)](references/card-design.md)。在將卡片寫入 Obsidian
筆記之前，也請閱讀 [外掛程式語法 (plugin syntax)](references/plugin-syntax.md)。

請使用使用者提供或選取的來源資料。若某項主張含糊不清或缺乏依據，切勿默認將其轉化為事實；請保留其不確定性，或告知使用者缺少了哪些資訊。

## 工作流程

1. Identify the user's learning goal and the part of the source in scope.
2. Find the durable ideas that are worth retrieving. Do not create cards for every sentence.
3. Check existing cards in the target note. Avoid exact and semantic duplicates.
4. Draft a clear cue and the smallest answer that fully satisfies it.
5. Choose the card type from the decision rules in `plugin-syntax.md`.
6. 請將卡片集中儲存在另一個筆記，不要混在原始文本內。

If the user asks only for suggestions or a preview, do not edit files. Show the proposed cards in Markdown instead.

## 外掛程式不變原則 (Plugin invariants)

- Obsidian 為主要的創作來源。切勿在 Anki 中直接編輯已連結的卡片內容。
- 切勿建立或修改受系統管理的 `flashcards` frontmatter 屬性。
- 切勿建立、複製或修改 `^q-xxxx` 或舊版的數字錨點。外掛程式擁有卡片識別碼的主導權，並會在更新時自動寫入這些值。
- 在編輯卡片周圍的內容時，請保留既有已產生的元資料 (Metadata)。
- 除非使用者要求，否則切勿執行 Obsidian 到 Anki 的更新。撰寫卡片與變更外部 Anki 狀態屬於獨立操作。
- 請使用最新的 v2 語法，切勿產生 v1 相容性語法。
