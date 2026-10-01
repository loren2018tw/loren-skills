# 技能腳本以 Python 單一實作，官方支援 Linux 與 Windows

技能內由 agent 執行的腳本一律以 Python（純標準庫）實作，不假設 bash 或 pwsh 存在；官方支援平台為 Linux 與 Windows，macOS 為 best-effort（不進 CI、文件不掛「已支援」）。跨平台行為以 CI 腳本層煙霧（ubuntu + windows runner；只涵蓋無重量依賴者）驗證，比照 ADR 0003 不依賴人工實機測試。

理由：agent 在 Windows 的執行 shell 不可控——OpenCode 的偵測序為 pwsh → Windows PowerShell 5.1 → Git Bash → cmd，未裝 pwsh 時實質是 5.1；Claude Code 優先用 Git Bash、否則用 PowerShell（同為 pwsh → 5.1）。且 `python3` 在 Windows 幾乎必是 Microsoft Store 執行別名，可靠的直譯器名稱是 `py`（python.org 安裝器預設提供）；bash 與 pwsh 都不保證存在。因此 SKILL.md 以平台分支呼叫（Windows `py -3`、macOS/Linux `python3`），腳本自身處理 UTF-8 輸出（非 UTF-8 pipe 如 CP950 不崩）與工具定位（PATH → 少量常見安裝位置 → 安裝指引）。

曾考慮：為 Windows 另寫 PowerShell 等效腳本（雙實作需同步維護，且等於要求使用者另裝 pwsh）；保留 bash 腳本、文檔化要求 Windows 用 Git Bash（bash 預設不在 PATH、`python3` 錯名問題仍在、macOS 的 GNU `readlink` 依賴也未解）。
