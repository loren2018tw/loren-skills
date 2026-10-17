# Wayground xlsx format

Wayground（原 Quizizz）以自己的試算表範本匯入題目（官方範本檔名
`Wayground Assessment Template.xlsx`，上傳後由平台解析）。下表幾何直接讀自該範本檔
（2026-10 拆解 `xl/worksheets/sheet1.xml`、`xl/sharedStrings.xml`）；官方線上文件未再查，
範本檔即本技能的唯一規格來源。

來源是 GimKit 匯出的 5 欄格式：`Question, Correct Answer, Incorrect Answer 1,
Incorrect Answer 2, Incorrect Answer 3` —— 其資料規則與 `create-gimkit-questions`
技能的輸出契約相同。

## Template geometry

| 位置 | 內容 |
|---|---|
| 工作表 | `Create a Quiz`（單一工作表） |
| 第 1 列 | 表頭：A=`Question Text`、B=`Question Type`、C~G=`Option 1~5`、H=`Correct Answer`、I=`Time in seconds`、J=`Image Link`、K=`Answer explanation` |
| 第 2 列 | 範本的說明列（每欄一段填寫說明），本工具留空 |
| 第 3 列起 | 一題一列；範本本身的資料驗證與條件格式範圍都從第 3 列開始（`B3:B1000`、`I3:I1000`、`A3:A102`…），範例題也佔第 3~10 列 |

## Field mapping (GimKit → Wayground)

| GimKit source column | Wayground output column |
|---|---|
| Question | A（Question Text） |
| Correct Answer | 放入 Option 1~4（C~F 欄），位置**輪替打散**（1→2→3→4） |
| Incorrect Answer 1~3 | 填入其餘選項欄 |
| —（無） | B（Question Type）= `Multiple Choice` |
| —（無） | H（Correct Answer）= 正解所在**選項編號** 1~4，不是答案文字 |
| —（無） | I（Time in seconds）= 秒數（範本註明預設 30） |
| —（無） | G（Option 5）、J（Image Link）、K（Answer explanation）留空 |

## Values the template pins down

- **題型下拉**（B3:B1000）＝ `Multiple Choice, Checkbox, Fill-in-the-Blank,
  Open-Ended, Poll, Draw, Reorder, Match`；範本說明「預設為 Multiple Choice」。
  本工具只產 `Multiple Choice`，且明確寫入而非留空。
- **時間下拉**（I3:I1000）＝ `5,10,20,30,45,60,120,180,300,900`；範本 I 欄說明
  `(optional, default value is 30 seconds)`。本工具只接受這組值，預設 30。
- **Correct Answer** ＝ 選項編號；Checkbox 題型用逗號分隔（範例 `1,2,3`），
  非選擇題型（Open-Ended／Poll／Draw／Fill-in-the-Blank／Match／Reorder）留空。
  本工具每題單一正解，故只寫一個數字。
- **範本未標示任何字數上限、題數上限或檔案大小限制**（驗證範圍畫到第 1000 列只是
  範本版面，不是平台限制），因此本腳本不做長度警告、也不設題數上限。

## 第 2 列留空的理由

範本第 2 列是填寫說明。匯入端若「從第 2 列起逐列讀、跳過空列」，空白的第 2 列會被略過；
若匯入端「固定跳過前兩列、從第 3 列起讀」（與範本自身的資料驗證範圍一致），也不受影響。
兩個假設下都安全；反之把題目寫進第 2 列，在前者會多一題、在後者會吃掉第一題。
若實際上傳後發現題目被吃掉或位移，把腳本常數 `FIRST_DATA_ROW` 調成 2 重跑即可
（純版面常數，不動轉換邏輯）。

## Verification gate

腳本輸出後**重讀自己寫出的 xlsx**，比對：

- 工作表名為 `Create a Quiz`；
- 檔內列號恰為「表頭第 1 列 + 第 3 列起每題一列」；
- 第 1 列表頭逐字與官方範本一致；
- 每題的題目文字、四個選項集合與來源一致；
- B 欄為 `Multiple Choice`、H 欄編號指向的選項確實是來源正解；
- 每題 I 欄秒數與參數一致；
- G／J／K 三欄留空。

全部通過才交出檔案；失敗時腳本 exit 1 並列出問題，修正後重跑，不要手工修補輸出檔。

xlsx 以標準庫 `zipfile` + XML 手寫（`inlineStr` 字串、無樣式），理由與做法同
`docs/adr/0006-kahoot-xlsx-stdlib-writer.md`。
