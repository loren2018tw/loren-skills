# 在 Windows PowerShell 5.1 下執行（CI 的 windows job 會呼叫）：
# 斷言 install.ps1 因 #Requires 版本需求乾淨失敗，且沒有執行到腳本主體。
# 本檔刻意不加 #Requires；以 UTF-8 BOM 存檔，5.1 才能正確解析中文。
$ErrorActionPreference = 'Continue'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$out = ''
try {
  $out = & (Join-Path $root 'install.ps1') -DryRun 2>&1 | Out-String
} catch {
  $out = $_ | Out-String
}
Write-Host $out
if ($out -notmatch '7\.2') { throw '5.1 執行時未出現 7.2 版本需求訊息' }
if ($out -match '\[資訊\]') { throw '5.1 竟執行了腳本主體（#Requires／BOM 失效？）' }
Write-Host '5.1 fail-fast OK：install.ps1 乾淨拒絕在 5.1 執行'
