# Windows 一律使用 PowerShell 7.2+，編碼與行尾以不變式鎖定

本 repo 的 Windows 安裝腳本（`install.ps1`）要求 PowerShell 7.2 以上（`#Requires -Version 7.2`），不再支援 Windows 內建的 PowerShell 5.1：5.1 缺少讀取連結目標所需的 API（`Target` 屬性、`Directory.ResolveLinkTarget`），會讓 `-Uninstall` 與陳舊連結清除靜默失效；而且 5.1 讀取無 BOM 的 UTF-8 腳本檔時會依系統代碼頁（zh-TW 為 CP950）解析，中文訊息變亂碼、甚至可能影響剖析。`install.cmd` 改為偵測器：尋找 `pwsh`（PATH、`%ProgramFiles%\PowerShell\7`、`%LOCALAPPDATA%\Microsoft\WindowsApps`）並檢查版本，合格才轉呼叫 `install.ps1`；找不到時只顯示安裝指引（`winget install -e --id Microsoft.PowerShell`、Microsoft Store、<https://aka.ms/powershell>）並以非零結束，不做任何修改。`install.ps1` 保留 UTF-8 BOM，讓 5.1 直接呼叫時 `#Requires` 給出乾淨的版本需求訊息，而非亂碼解析錯誤。

編碼與行尾以不變式鎖定，交由 `.gitattributes`／`.editorconfig` 強制：`*.ps1` 為 UTF-8 with BOM、工作區 CRLF；`*.cmd`／`*.bat` 為純 ASCII、無 BOM、CRLF；其餘文字檔 UTF-8 無 BOM、LF。行為驗證交給 CI（`.github/workflows/checks.yml`）在真實平台執行：Linux 跑 `install.sh` 生命週期，Windows 以 PowerShell 7 跑 junction 生命週期與外來連結保護，並斷言 5.1 會乾淨失敗——維護者的開發機是 Linux，不靠人工實機測試。

曾考慮：支持 5.1（需要三段式連結目標偵測鏈與雙引擎測試矩陣，成本高）；`install.cmd` 改用 UTF-8 中文訊息＋`chcp 65001`（須放棄 ASCII 不變式，且會改動使用者的主控台代碼頁）；統一以 pwsh 執行 Linux 端安裝（等於強迫 Linux 使用者安裝 pwsh，成本更高）。
