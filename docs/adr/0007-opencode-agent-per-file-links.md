# OpenCode agents 以逐檔連結安裝，Windows 用檔案符號連結

本 repo 的 OpenCode agents 與輔助腳本以逐檔連結安裝到 OpenCode 設定根目錄（`OPENCODE_CONFIG_DIR`，未設定時為 `$XDG_CONFIG_HOME/opencode` 或 `~/.config/opencode`）的 `agents/` 與 `bin/`，不連結整個目錄。原因：`agents/` 可能已有使用者自己的 agent（本機即為 `remote.md`），整目錄連結會取代或隱藏它；逐檔連結也讓卸載與清除陳舊連結能嚴格以「連結目標是否位於本 repo 的 `opencode/agents`／`opencode/bin`」判定所有權，不動其他檔案。安裝任一 agent 時一併連結 `opencode/bin/*.py`，因為 agent 的提示詞直接呼叫這些輔助腳本。

Windows 沒有可連結單一檔案又不需權限的 junction；本專案選擇檔案符號連結（symlink），而不是 hardlink 或複本。hardlink 在 `git pull` 以新檔取代舊檔時會斷開，複本則失去「更新即時生效」的承諾；兩者都會讓安裝結果與 repo 靜默漂移。代價是 Windows 使用者需開啟 Developer Mode 或以管理員身分執行；連結失敗時安裝腳本明確報錯並給出指引，不默默降級。CI 以系統管理員權限執行，因此能驗證 symlink 路徑。

曾考慮：把整個 `agents/` 換成 junction（拒絕：會蓋掉使用者的 agent，且 nested path 會改變 agent ID）；Windows 用 hardlink（拒絕：git pull 後連結失效）；Windows 用複本（拒絕：失去連結安裝的即時更新）；把 agent 放進子目錄再 junction（拒絕：OpenCode 會把目錄名併入 agent ID）。
