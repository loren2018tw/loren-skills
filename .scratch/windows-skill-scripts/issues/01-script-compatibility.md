# 技能內腳本的非 Linux 平台相容性

Status: needs-triage

## 背景

技能內由 agent 執行的腳本目前假設 Unix 環境：

- `doc-to-markdown-with-image/scripts/doc-to-md.sh`：`#!/usr/bin/env bash`，依賴 bash 環境與 GNU 工具（`readlink -f --`、`mktemp -d`）；macOS 內建 `readlink` 不支援 `-f`。
- 兩支 `SKILL.md` 寫死 `bash scripts/…` 與 `python3 scripts/…`；Windows 上的 Python 指令通常是 `py -3` 或 `python`。
- `merge_md_images.py`、`convert_to_blooket.py` 為純標準庫 Python，本身大致跨平台，但 Windows 的 stdout 編碼（CP950 主控台／pipe）可能使中文輸出失敗或亂碼。

## 待決

- 支援目標平台是哪幾個（Windows？macOS？）
- 提供 PowerShell 等效腳本、改寫成 Python-only、或以文件化依賴（Git Bash／WSL＋python3）處理
- agent 在 Windows 上的執行 shell 是什麼（未經實機確認）

（本票出自 `grill-with-docs` 會談：安裝工具鏈收斂為 PowerShell 7 之後，特意留出的範圍外後續。）
