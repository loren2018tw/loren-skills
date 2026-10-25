# loren-skills

Loren 自製的 agent 技能與 OpenCode agents 收藏倉。

## 技能列表

- **who-is-loren**: 關於作者本人的基本事實（姓名、email、GitHub、興趣）。agent 需要稱呼或介紹 Loren 時使用。
- **doc-to-markdown-with-image**: 把 Word 文件（.docx／舊版 .doc 經 LibreOffice 橋接）轉成簡潔 markdown，內嵌圖片抽出成實體檔、群組示意圖的文字繪回圖上，以相對路徑引用。
- **textbook-analysis**: 把課本章節、講義、題目與參考答案透析成結構化知識（核心概念、概念關係、考題辨識、解題邏輯、易錯陷阱、一分鐘背誦版），輸出為與原始文本分離的獨立 markdown 檔。
- **create-gimkit-questions**: 把文本、筆記、文件轉成 GimKit 可匯入的四選一單選題 CSV。
- **gimkit-to-blooket**: 把 GimKit 匯出的題庫 CSV 轉成 Blooket 官方匯入範本格式（含 Time Limit、正解位置輪替與匯入前驗證）。
- **gimkit-to-kahoot**: 把 GimKit 匯出的題庫 CSV 轉成 Kahoot 匯入用的 .xlsx（官方模板版面、Time limit、正解位置輪替與匯入前驗證）。
- **gimkit-to-wayground**: 把 GimKit 匯出的題庫 CSV 轉成 Wayground（原 Quizizz）匯入用的 .xlsx（官方範本版面、Time in seconds、正解位置輪替與匯入前驗證）。
- **create-flashcards**: 在 Obsidian 筆記內建立有效的 Anki 記憶卡（Flashcards plugin v2 語法）。

> 技能與 OpenCode agent 的輔助腳本官方支援 Linux 與 Windows；macOS 為 best-effort（可用但未經 CI 驗證）。

## OpenCode agents

本倉庫也提供兩個可直接安裝到 OpenCode 的自訂 agents：

- **geminiimage**: 使用 OpenRouter 的 Gemini 3.1 Flash Image（Nano Banana 2）生成與編輯圖片。
- **gptimage**: 使用 OpenRouter 的 GPT Image 2.5 Sunburst 生成與編輯圖片。

agent 定義在 `opencode/agents/*.md`，提示詞呼叫的輔助腳本在 `opencode/bin/*.py`。安裝時逐檔連結到 OpenCode 設定根目錄的 `agents/` 與 `bin/`；預設根目錄是 `~/.config/opencode`，也支援 `OPENCODE_CONFIG_DIR` 與 `XDG_CONFIG_HOME`。目標目錄中既有的 agent、腳本與其他檔案不會被覆蓋。

> 這兩個 agent 需要 OpenRouter 的 API key；輔助腳本會依序讀取 `OPENROUTER_API_KEY`、OpenCode 的 credential store，以及舊版 `~/.local/share/opencode/auth.json`。

## 安裝

技能以目錄連結安裝；OpenCode agent 與輔助腳本以逐檔連結安裝。安裝後在本倉庫 `git pull`，OpenCode 端即時生效，不需重裝。

> 建議以 `git clone` 取得本倉庫，而非下載 zip：連結安裝的即時更新靠 `git pull`，zip 副本沒有這個管道。

### Linux / macOS

```bash
./install.sh                       # 全量安裝（技能＋agents）
./install.sh who-is-loren          # 只安裝指定技能
./install.sh geminiimage           # 只安裝指定 agent（含 bin 輔助腳本）
./install.sh --agents              # 只安裝 agents 與輔助腳本
./install.sh --skills              # 只安裝技能
./install.sh --dry-run             # 只預覽，不做任何修改
./install.sh --uninstall           # 移除所有指向本倉庫的連結
./install.sh --uninstall --agents  # 只移除 agents 與輔助腳本
./install.sh --help                # 完整用法
```

- `--target DIR`：改變技能安裝位置（預設 `~/.agents/skills`）。
- `--opencode-dir DIR`：改變 OpenCode 設定根目錄（預設依 `OPENCODE_CONFIG_DIR`、`$XDG_CONFIG_HOME/opencode`、`~/.config/opencode` 順序決定）。若自訂此值，OpenCode 端也需以相同的 `OPENCODE_CONFIG_DIR` 啟動，才會掃到 agent。
- 目標已有同名**實體項目**或**非本倉庫的連結**時報錯跳過；`--force` 會先備份成 `<名稱>.bak-<時間戳>` 再建立連結。
- 全量安裝會自動清除「指向本倉庫但項目已不存在」的陳舊連結，且只處理本倉庫擁有的連結。
- Git Bash／MSYS 下 `ln -s` 不是真正的連結，腳本會直接拒絕執行，請改用 PowerShell。

### Windows

需要 **PowerShell 7.2 以上（pwsh）**。任選一種安裝方式：

```powershell
winget install -e --id Microsoft.PowerShell   # 一行搞定（會跳 UAC 提權）
```

或從 Microsoft Store 搜尋「PowerShell」（不需管理員權限），或下載 <https://aka.ms/powershell> 的 MSI／免安裝 zip。

Windows 預設的執行原則（Restricted）會擋下 `.ps1`，直接執行 `.\install.ps1` 會出現「因為這個系統上已停用指令碼執行，所以無法載入……」的錯誤。最簡單的方式是改用 `install.cmd`，它會先確認 `pwsh` 存在、版本足夠，再以 `Bypass` 原則呼叫 `install.ps1`：

```bat
.\install.cmd -DryRun                      :: 先預覽
.\install.cmd
.\install.cmd -Skills who-is-loren
.\install.cmd -Skills geminiimage
.\install.cmd -OnlySkills
.\install.cmd -OnlyAgents
.\install.cmd -Uninstall
.\install.cmd -Uninstall -OnlyAgents
.\install.cmd -OpencodeDir "D:\opencode-config"
```

- `-Skills` 接受技能或 agent 名稱；`-OnlySkills`／`-OnlyAgents` 是類別篩選。
- 技能以**目錄連接點（junction）**安裝，不需要管理員權限。
- agent `.md` 與 `bin/*.py` 是單一檔案，Windows 以**檔案符號連結（symlink）**安裝，需開啟 **Developer Mode** 或以管理員身分執行。連結失敗時腳本會明確報錯，不會改用 hardlink／複本降級。
- `.lnk` 捷徑不是檔案系統連結，agent 不會跟隨，因此不採用。

找不到 `pwsh`（或版本太舊）時，`install.cmd` 不會做任何修改，只會顯示安裝指引。已裝好 PowerShell 7 的人也可以直接呼叫：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
```

若只想在目前這個 PowerShell 工作階段放行，可先執行 `Set-ExecutionPolicy -Scope Process Bypass`，再以 pwsh 執行 `.\install.ps1`。

> 兩平台的安裝腳本都由 CI（`.github/workflows/checks.yml`）在真實平台執行驗證：Linux 跑 `install.sh` 生命週期，Windows 以 PowerShell 7 跑 junction 與檔案 symlink 生命週期，並確認 Windows PowerShell 5.1 會乾淨地拒絕執行。

### 手動安裝

技能：

```bash
ln -s "$PWD/<技能名>" ~/.agents/skills/<技能名>
```

OpenCode agents 與輔助腳本（逐檔連結）：

```bash
mkdir -p ~/.config/opencode/agents ~/.config/opencode/bin
ln -s "$PWD/opencode/agents/geminiimage.md" ~/.config/opencode/agents/
ln -s "$PWD/opencode/agents/gptimage.md" ~/.config/opencode/agents/
ln -s "$PWD/opencode/bin/geminiimage.py" ~/.config/opencode/bin/
ln -s "$PWD/opencode/bin/gptimage.py" ~/.config/opencode/bin/
```
