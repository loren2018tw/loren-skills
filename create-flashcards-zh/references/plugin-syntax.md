# Flashcards 外掛程式 v2 語法

在將卡片寫入筆記之前，請先閱讀本參考文件。以下皆為撰寫時使用的形式；
識別碼中繼資料 (Identity Metadata) 會由外掛程式在更新時自動加入。

## 選擇卡片類型

| 需求 | 建議形式 |
| --- | --- |
| 簡短的問答 | 行內基礎卡 (Inline basic) |
| 正反兩個方向都有用 | 行內或圍欄反轉卡 (Inline or fenced reversed) |
| 在上下文中回憶缺失的內容 | 克漏字卡 (Cloze) |
| 同一主題下的多區塊答案 | 標籤標題卡 (Hashtag heading) |
| 明確且精確的邊界 | 圍欄卡 (Fenced card) 或卡片呼叫框 (Card callout) |
| 某個原則需要定期重現 | 提醒卡 (Reminder) |
| 整篇筆記刻意只表達一個概念 | 原子筆記卡 (Atomic note) |
| 同一個主張值得以多種方式提問 | 原子筆記卡，多個 `test:` 項目 |

## 行內卡片

基礎卡：

```markdown
What is the capital of France?::Paris
```

反轉卡：

```markdown
TCP:::Transmission Control Protocol
```

清單項目中的行內卡會擁有該項目及其縮排的子區塊。
位於相同縮排層級的相鄰項目則會開始一張獨立的卡片。

## 克漏字卡

```markdown
The mitochondria is the ==powerhouse== of the cell.
The {1:heart} pumps blood through the {1:circulatory system}.
```

`==text==` 使用自動編號。`{N:text}` 使用明確編號。當多個片段應一併隱藏時，
請重複使用相同的 `N`。也支援原生的 `{{cN::text}}` 語法。

克漏字應保留在能指出預期答案的句子或其他上下文中。切勿僅為了從複製的
文章中移除任意單字而使用克漏字。

## 圍欄卡片

基礎卡或反轉卡：

````markdown
```flashcard
front: What does CSS stand for?
back: Cascading Style Sheets
type: reversed
```
````

`type` 為選填，預設為 `basic`。支援的值有 `basic`、`reversed`、`cloze` 與
`reminder`。

克漏字圍欄使用 `front` 作為 Anki 的 Text 欄位，選填的 `back` 則成為 Extra
欄位。提醒卡圍欄使用單一 `content` 欄位：

````markdown
```flashcard
type: reminder
content: Prefer reversible decisions when uncertainty is high.
```
````

## 標籤卡片

```markdown
## What is recursion? #card

A function that calls itself and has a base case.
```

反轉卡請使用 `#card-reverse` 或 `#card/reverse`。標記可以放在緊接標題之後
的獨立一行。

標題卡擁有其完整章節。較低層級的標題會保留在答案中。相同或更高層級的
標題則會結束該答案。

帶有 `#card` 的段落會使用標記之後同一段落內的文字。若段落內沒有其他文字，
則會使用下一個頂層 Markdown 區塊。較長的答案請使用標題或明確的容器。

## 提醒卡片

```markdown
Keep the feedback loop short. #card-reminder
```

提醒卡只有內容而沒有答案。提醒卡段落僅擁有該段落本身。不支援 v1 的
`#card-spaced` 語法。

## 卡片呼叫框

```markdown
> [!CARD] : What is recursion?
> A function that calls itself.
>
> It needs a base case.
```

呼叫框是一個明確的容器。其標題即為問題，內文則為答案。

## 原子筆記卡片

僅在筆記被刻意撰寫為單一張卡片時，才使用原子語法。答案一律是內文的第一
個段落。第一個段落之後的所有內容都不會被讀取。

請以字串清單的形式撰寫 `test:`。單一裸純量 (Bare scalar) 也會被接受並正規
化為單一項目的清單，但清單形式才是慣例——它能讓 Obsidian 屬性面板在各筆
記之間保持一致。

```markdown
---
test:
  - Define recursion
---

A function that calls itself and has a base case.
```

每個項目會產生一張卡片。項目可以是保留關鍵字，或你自行撰寫的問題：

| 項目 | 問題 | 結果 |
| --- | --- | --- |
| `title` | 檔案名稱 | 基礎卡 |
| `reversed` | 檔案名稱與第一個段落，正反兩個方向 | 一則筆記，兩張卡片 |
| `cloze` | 第一個段落並隱藏其中的 `==spans==` | 克漏字卡 |
| 其他任何字串 | 該字串 | 基礎卡 |

多個項目可以從不同角度對同一個主張提問，並共用同一個答案：

```markdown
---
test:
  - title
  - "Re-reading feels productive. What does it fail at?"
---
```

該筆記會產生兩張共用同一答案的卡片。僅在提示針對的是*同一個*主張時才
使用多個項目。若提示需要不同的答案，代表該筆記不是原子的——請將它拆分。

若違反以下規則，將靜默地產生零張卡片。寫入前請先檢查：

- 項目必須是唯一的。重複的項目會使整個 `test:` 鍵失效。
- 自行撰寫的問題不得等同於檔案名稱，也不得與其他項目衍生的內容重複。
  兩者都會與 `title` 產生的卡片衝突。
- `reversed` 與 `cloze` 各自最多只能出現一次。
- 巢狀映射 (Nested maps) 或非字串項目視為錯誤，絕不猜測處理。

以下兩種情況會回報為警告，且不會更動筆記：`test:` 鍵存在但沒有第一個段
落，以及 `cloze` 項目的第一個段落中不含任何 `==span==`。

沒有 `test:` 鍵的筆記不是卡片。對於橋接筆記 (Bridge notes)、結構筆記
(Structure notes)，以及任何價值在於其連結的筆記而言，這是正確的預設狀態。

## 邊界與優先順序

明確的卡片容器擁有其來源範圍。該範圍內類似卡片的文字屬於內容，而非另
一張卡片。

優先順序為：

1. 原子筆記卡、圍欄卡與卡片呼叫框。
2. 標籤卡。
3. 行內清單卡及其子區塊。
4. 行內反轉卡。
5. 行內基礎卡。
6. 克漏字卡。

切勿在容器內放置第二張卡片。請先結束第一個容器，再開始下一張卡片。

## 牌組、標籤與上下文

明確指定筆記牌組的方式：

```yaml
---
cards-deck: Knowledge::Biology
tags:
  - biology
  - exam
---
```

若未指定 `cards-deck`，預設會啟用資料夾式牌組。最終的後備牌組為
`Default`。預設標籤為 `obsidian`。上層標題是複習問題上方顯示的預設上下文。

## 受系統管理的中繼資料

請勿撰寫或編輯以下值：

- `flashcards` frontmatter 屬性；
- `^q-xxxx` 錨點；
- 舊版數字錨點；
- Anki 筆記 ID、來源雜湊值 (Source hashes) 或同步雜湊值 (Sync hashes)。

這些值由外掛程式建立與維護。編輯筆記時請保留既有值。

完整的邊界情況請閱讀儲存庫中的 `docs/wiki.md`。
