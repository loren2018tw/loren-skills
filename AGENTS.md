## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles with label strings equal to their names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### 跨平台腳本不變式

- `*.ps1`：UTF-8 **with BOM**、`#Requires -Version 7.2`；Windows 一律以 PowerShell 7（`pwsh`）執行，不支援 Windows PowerShell 5.1。
- 技能內腳本一律 Python（純標準庫）單一實作；agent 呼叫：Windows 用 `py -3`、macOS/Linux 用 `python3`；不得假設 `bash`／`pwsh` 存在。技能腳本煙霧測試：Windows `py -3 tests/script-smoke.py`、macOS/Linux `python3 tests/script-smoke.py`。詳見 `docs/adr/0004-python-only-skill-scripts.md`。
- `*.cmd` / `*.bat`：純 ASCII、**無 BOM**（cmd.exe 會把 BOM 當指令解讀）。
- 其餘文字檔（`.sh`、`.py`、`.md`…）：UTF-8 無 BOM、LF。
- 編碼與行尾由 `.gitattributes`／`.editorconfig` 鎖定；改動後跑 `bash tests/check-encoding.sh`，CI 亦會驗。
- 需要 Windows 才能驗的行為（junction、執行原則）交給 CI 跑，不要只在 Linux 上靠推論。詳見 `docs/adr/0003-pwsh-7-and-encoding-invariants.md`。
