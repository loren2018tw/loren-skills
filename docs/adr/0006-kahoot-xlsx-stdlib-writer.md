# Kahoot 轉換輸出 .xlsx：標準庫手寫、複刻官方模板版面

Kahoot 的試算表匯入只接受 `.xlsx`（MS Excel 2007 或更新），沒有 CSV 匯入管道：現行官方文章寫 *"Save the template as a .xlsx file"*、模板本身寫 *"if you're not using Excel you need to export to .xlsx format before you upload"*，說明中心也搜不到任何 CSV 匯入文章（網路上的「Kahoot CSV」說法全出自第三方）。因此 `gimkit-to-kahoot` 技能的產物固定為 `.xlsx`，並且以純標準庫 `zipfile` + XML 直接寫出最小工作簿（`inlineStr` 字串、無樣式、固定 zip 時間戳），不引入 openpyxl，維持 ADR 0004 的「技能腳本純標準庫」政策。輸出後由腳本重讀自己寫出的檔案逐題比對來源，通過才交出檔案。

版面比照官方模板的固定幾何：表頭在第 8 列（B=`Question`、C~F=`Answer 1~4`、G=`Time limit`、H=`Correct answer(s)`），資料自第 9 列起，工作表名 `Sheet1`；後續以 LibreOffice 讀回驗證過互通性。

理由：Kahoot 是唯一沒有 CSV 管道的下游平台，而「先產 CSV 再叫使用者手動另存」等於交出不可匯入的檔案；純標準庫足以寫出合法 xlsx（五個 XML part），換來零安裝依賴與既有的 `py -3`／`python3` 呼叫慣例。

曾考慮：輸出 CSV 並在文件指示使用者另存 xlsx（多一道手動步驟、CSV 對中文還有編碼風險，且本技能被要求的就是「可直接匯入」）；改用 openpyxl（要 pip 安裝、脫離純標準庫政策，換來的只是省下幾十行 XML 樣板）；安裝時複製官方模板檔再填入題目（需散布官方二進位檔、版面會隨官方改版漂移，自行產生最小檔案反而可控）。
