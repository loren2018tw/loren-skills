# 技能以連結安裝，與 vercel CLI 的複本安裝並存

本 repo 的技能以檔案系統連結（Unix symlink／Windows junction）安裝到目標技能庫（`~/.agents/skills`），而非複本——技能是持續編輯的內容，連結讓 `git pull` 即時反映到 agent，重裝步驟歸零。同一個目標技能庫另有 vercel skills CLI 以複本管理的外部技能，兩種機制並存：安裝腳本對同名實體目錄一律報錯（除非 `--force` 並先備份），不與複本管理器搶所有權。曾考慮複本安裝（放棄：每次改技能都要重跑安裝）與 Windows `.lnk` 捷徑（放棄：不是檔案系統連結，agent 掃描不到）。
