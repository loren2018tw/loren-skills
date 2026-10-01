# loren-skills

Loren 自製的 agent 技能收藏倉。

## 技能列表

- **who-is-loren**: 關於作者本人的基本事實（姓名、email、GitHub、興趣）。agent 需要稱呼或介紹 Loren 時使用。
- **doc-to-markdown-with-image**: 把 Word 文件（.docx／舊版 .doc 經 LibreOffice 橋接）轉成簡潔 markdown，並把內嵌圖片抽出成實體檔、以相對路徑引用。
- **textbook-analysis**: 把課本章節、講義、題目與參考答案透析成結構化知識（核心概念、概念關係、考題辨識、解題邏輯、易錯陷阱、一分鐘背誦版），輸出為與原始文本分離的獨立 markdown 檔。
- **create-gimkit-questions**: 把文本、筆記、文件轉成 GimKit 可匯入的四選一單選題 CSV。
- **gimkit-to-blooket**: 把 GimKit 匯出的題庫 CSV 轉成 Blooket 官方匯入範本格式（含 Time Limit、正解位置輪替與匯入前驗證）。
- **create-flashcards**: 在 Obsidian 筆記內建立有效的 Anki 記憶卡（Flashcards plugin v2 語法）。

## 安裝

每個技能是一個目錄，內含 `SKILL.md`。安裝＝在目標技能庫（預設 `~/.agents/skills`）建立指向本倉庫技能目錄的連結；之後在本倉庫 `git pull`，agent 端即時生效，不需重裝。

> 建議以 `git clone` 取得本倉庫，而非下載 zip：連結安裝的即時更新靠 `git pull`，zip 副本沒有這個管道。

### Linux / macOS

```bash
./install.sh                       # 全量安裝（自動偵測根目錄下含 SKILL.md 的技能）
./install.sh who-is-loren          # 只安裝指定技能（可多個）
./install.sh --dry-run             # 只預覽，不做任何修改
./install.sh --uninstall           # 移除所有指向本倉庫的連結
./install.sh --help                # 完整用法
```

- `--target DIR`：改變安裝位置（預設 `~/.agents/skills`）。
- 目標已有同名**實體項目**時報錯跳過；`--force` 會先備份成 `<名稱>.bak-<時間戳>` 再建立連結。
- 全量安裝會自動清除「指向本倉庫但技能已不存在」的陳舊連結。
- Git Bash／MSYS 下 `ln -s` 不是真正的連結，腳本會直接拒絕執行，請改用 PowerShell。

### Windows

需要 **PowerShell 7.2 以上（pwsh）**。任選一種安裝方式：

```powershell
winget install -e --id Microsoft.PowerShell   # 一行搞定（會跳 UAC 提權）
```

或從 Microsoft Store 搜尋「PowerShell」（不需管理員權限），或下載 <https://aka.ms/powershell> 的 MSI／免安裝 zip。

Windows 預設的執行原則（Restricted）會擋下 `.ps1`，直接執行 `.\install.ps1` 會出現「因為這個系統上已停用指令碼執行，所以無法載入……」的錯誤。最簡單的方式是改用 `install.cmd`，它會先確認 `pwsh` 存在、版本足夠，再以 `Bypass` 原則呼叫 `install.ps1`：

```bat
.\install.cmd -DryRun                 :: 先預覽
.\install.cmd
.\install.cmd -Skills who-is-loren
.\install.cmd -Uninstall
```

找不到 `pwsh`（或版本太舊）時，`install.cmd` 不會做任何修改，只會顯示安裝指引。已裝好 PowerShell 7 的人也可以直接呼叫：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
```

若只想在目前這個 PowerShell 工作階段放行，可先執行 `Set-ExecutionPolicy -Scope Process Bypass`，再以 pwsh 執行 `.\install.ps1`。

Windows 以**目錄連接點（junction）**實作，不需要管理員權限；`.lnk` 捷徑不是檔案系統連結，agent 不會跟隨，因此不採用。

> 兩平台的安裝腳本都由 CI（`.github/workflows/checks.yml`）在真實平台執行驗證：Linux 跑 `install.sh` 生命週期，Windows 以 PowerShell 7 跑 junction 生命週期，並確認 Windows PowerShell 5.1 會乾淨地拒絕執行。

### 手動安裝

```bash
ln -s "$PWD/<技能名>" ~/.agents/skills/<技能名>
```
