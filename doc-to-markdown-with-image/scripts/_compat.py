#!/usr/bin/env python3
"""doc-to-markdown-with-image 技能腳本共用小工具：工具定位與 UTF-8 輸出。只用 Python 標準庫。"""
import os
import shutil
import sys
from pathlib import Path

# 常見安裝位置（PATH 找不到時才查）：
# LibreOffice 的標準安裝路徑（Windows / macOS）與 uv tool 的 shim 目錄。
_CANDIDATES = {
    'soffice': [
        Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'LibreOffice' / 'program' / 'soffice.exe',
        Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'LibreOffice' / 'program' / 'soffice.exe',
        Path('/Applications/LibreOffice.app/Contents/MacOS/soffice'),
    ],
    'markitdown': [
        Path.home() / '.local' / 'bin' / 'markitdown',
        Path.home() / '.local' / 'bin' / 'markitdown.exe',
    ],
}


def common_tool_location(name):
    """只查常見安裝位置（不含 PATH）：回傳可執行路徑（str）或 None。"""
    for candidate in _CANDIDATES.get(name, ()):
        if candidate.is_file():
            return str(candidate)
    return None


def find_tool(name):
    """回傳可執行路徑（str）：先查 PATH，再查少量常見安裝位置；找不到回 None。"""
    exe = shutil.which(name)
    if exe:
        return exe
    return common_tool_location(name)


def use_utf8_stdio():
    """stdout/stderr 明確以 UTF-8 輸出：非 UTF-8 主控台／pipe（如 zh-TW Windows 的 CP950）不崩。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
