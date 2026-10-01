#Requires -Version 5.1
<#
.SYNOPSIS
  將本倉庫的技能以目錄連接點（junction）安裝到目標技能庫（預設 ~\.agents\skills）。

.DESCRIPTION
  語意與 install.sh 對齊。Windows 以 junction 實作：對檔案系統 API 透明、
  不需要管理員權限；.lnk 捷徑不是檔案系統連結，agent 掃描不到，因此不採用。

  注意：本腳本尚未在 Windows 實機驗證，建議先以 -DryRun 預覽。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Skills who-is-loren
#>
[CmdletBinding()]
param(
  [string]$Target,
  [string[]]$Skills = @(),
  [switch]$Uninstall,
  [switch]$Force,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Root     = [System.IO.Path]::GetFullPath($PSScriptRoot)
$RootFull = $Root.TrimEnd('\', '/')

if (-not $Target) { $Target = Join-Path $HOME '.agents\skills' }
$Target = [System.IO.Path]::GetFullPath($Target).TrimEnd('\', '/')

$script:created = 0; $script:updated = 0; $script:unchanged = 0
$script:backed = 0; $script:pruned = 0; $script:removed = 0; $script:failed = 0

function Fail([string]$Message) {
  Write-Host "[錯誤] $Message" -ForegroundColor Red
  exit 1
}

function Get-LinkTarget($Path) {
  try {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  } catch {
    return $null
  }
  if ($item.PSObject.Properties['Target'] -and $item.Target) { return [string]$item.Target }
  try {
    $resolved = [System.IO.Directory]::ResolveLinkTarget($Path, $false)
    if ($resolved) { return $resolved.FullName }
  } catch { }
  return $null
}

function Test-Ours($Path) {
  $t = Get-LinkTarget $Path
  if (-not $t) { return $false }
  try { $t = [System.IO.Path]::GetFullPath($t) } catch { return $false }
  $t = $t.TrimEnd('\', '/')
  $r = $RootFull + [System.IO.Path]::DirectorySeparatorChar
  return $t.StartsWith($r, [System.StringComparison]::OrdinalIgnoreCase)
}

function Remove-Link($Path) {
  $item = Get-Item -LiteralPath $Path -Force
  if ($item.Attributes -band [System.IO.FileAttributes]::Directory) {
    & cmd.exe /c rmdir "$Path" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "移除連結失敗：$Path" }
  } else {
    Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
  }
}

function New-Junction([string]$Link, [string]$Src) {
  try {
    New-Item -ItemType Junction -Path $Link -Target $Src -ErrorAction Stop | Out-Null
  } catch {
    & cmd.exe /c mklink /J "$Link" "$Src" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "建立連結失敗：$Link" }
  }
}

function Install-OneSkill([string]$Name) {
  $src  = Join-Path $Root $Name
  $link = Join-Path $Target $Name

  $item = $null
  try { $item = Get-Item -LiteralPath $link -Force -ErrorAction Stop } catch { $item = $null }
  $isLink = $false
  if ($item) { $isLink = [bool]($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) }

  if ($isLink) {
    $cur = Get-LinkTarget $link
    if ($cur -and ([System.IO.Path]::GetFullPath($cur).TrimEnd('\', '/') -ieq $src.TrimEnd('\', '/'))) {
      Write-Host "[已最新] $Name"
      $script:unchanged++
      return
    }
    if ($DryRun) { Write-Host "[預覽] 重指 $Name -> $src"; $script:updated++; return }
    try { Remove-Link $link } catch {
      Write-Host "[失敗] 無法重指 $Name：$_" -ForegroundColor Red; $script:failed++; return
    }
    try { New-Junction $link $src } catch {
      Write-Host "[失敗] 無法重指 $Name：$_" -ForegroundColor Red; $script:failed++; return
    }
    Write-Host "[重指] $Name -> $src"
    $script:updated++
    return
  }

  if ($item) {
    if (-not $Force) {
      Write-Host "[跳過] $Name：目標已有實體項目，未覆蓋（可加 -Force 先備份再安裝）" -ForegroundColor Yellow
      $script:failed++
      return
    }
    $bak = "$link.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
    if ($DryRun) {
      Write-Host "[預覽] 備份 $Name 後安裝（備份名：$(Split-Path -Leaf $bak)）"
      $script:backed++
      return
    }
    try {
      Move-Item -LiteralPath $link -Destination $bak -ErrorAction Stop
      New-Junction $link $src
    } catch {
      Write-Host "[失敗] 無法備份後安裝 $Name：$_" -ForegroundColor Red; $script:failed++; return
    }
    Write-Host "[備份後安裝] $Name（原項目 -> $(Split-Path -Leaf $bak)）"
    $script:backed++
    return
  }

  if ($DryRun) { Write-Host "[預覽] 新增 $Name -> $src"; $script:created++; return }
  try { New-Junction $link $src } catch {
    Write-Host "[失敗] 無法建立連結 $Name：$_" -ForegroundColor Red; $script:failed++; return
  }
  Write-Host "[安裝] $Name -> $src"
  $script:created++
}

function Get-TargetLinks {
  if (-not (Test-Path -LiteralPath $Target -PathType Container)) { return @() }
  return @(Get-ChildItem -LiteralPath $Target -Force -ErrorAction Stop |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
}

function Invoke-Prune {
  foreach ($l in Get-TargetLinks) {
    if ($skillNames -contains $l.Name) { continue }
    if (-not (Test-Ours $l.FullName)) { continue }
    if ($DryRun) { Write-Host "[預覽] 清除陳舊連結 $($l.Name)"; $script:pruned++; continue }
    try { Remove-Link $l.FullName; Write-Host "[清除陳舊] $($l.Name)"; $script:pruned++ }
    catch { Write-Host "[失敗] 無法清除陳舊連結 $($l.Name)：$_" -ForegroundColor Red; $script:failed++ }
  }
}

function Invoke-Uninstall {
  foreach ($l in Get-TargetLinks) {
    if ($Skills.Count -gt 0 -and ($Skills -notcontains $l.Name)) { continue }
    if (-not (Test-Ours $l.FullName)) { continue }
    if ($DryRun) { Write-Host "[預覽] 移除連結 $($l.Name)"; $script:removed++; continue }
    try { Remove-Link $l.FullName; Write-Host "[移除] $($l.Name)"; $script:removed++ }
    catch { Write-Host "[失敗] 無法移除連結 $($l.Name)：$_" -ForegroundColor Red; $script:failed++ }
  }
}

# ---- 目標檢查 ---------------------------------------------------------------
$sep = [System.IO.Path]::DirectorySeparatorChar
if ($Target -eq $RootFull -or
    $Target.StartsWith($RootFull + $sep, [System.StringComparison]::OrdinalIgnoreCase)) {
  Fail "目標技能庫不能位於本倉庫內：$Target"
}
if ((Test-Path -LiteralPath $Target) -and -not (Test-Path -LiteralPath $Target -PathType Container)) {
  Fail "目標技能庫不是目錄：$Target"
}

# ---- 技能偵測 ---------------------------------------------------------------
$skillNames = @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction Stop |
  Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
  ForEach-Object { $_.Name })
if ($skillNames.Count -eq 0) { Fail '根目錄下找不到任何含 SKILL.md 的技能目錄' }

# ---- 主流程 -----------------------------------------------------------------
Write-Host "[資訊] 本倉庫：$Root"
Write-Host "[資訊] 目標技能庫：$Target"
if ($DryRun) { Write-Host '[資訊] dry-run：只預覽，不做任何修改' }

if ($Uninstall) {
  Invoke-Uninstall
  Write-Host ("完成：移除 {0}、失敗 {1}" -f $script:removed, $script:failed)
  if ($script:failed -gt 0) { exit 1 }
  exit 0
}

if ($Skills.Count -gt 0) {
  foreach ($s in $Skills) {
    if ($skillNames -notcontains $s) {
      Fail "不是可安裝的技能：$s（可安裝：$($skillNames -join '、')）"
    }
  }
}

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
  if ($DryRun) {
    Write-Host "[預覽] 建立目標技能庫 $Target"
  } else {
    New-Item -ItemType Directory -Path $Target -Force -ErrorAction Stop | Out-Null
  }
}

if ($Skills.Count -eq 0) { Invoke-Prune }

$selected = if ($Skills.Count -eq 0) { $skillNames } else { @($skillNames | Where-Object { $Skills -contains $_ }) }
foreach ($s in $selected) { Install-OneSkill $s }

Write-Host ("完成：新增 {0}、重指 {1}、已最新 {2}、備份 {3}、清除陳舊 {4}、失敗 {5}" -f `
  $script:created, $script:updated, $script:unchanged, $script:backed, $script:pruned, $script:failed)

if (-not $DryRun -and ($script:created + $script:updated + $script:backed) -gt 0) {
  Write-Host '提示：連結即時生效；若 agent 端有技能清單快取，重開 session 即可看到。'
}

if ($script:failed -gt 0) { exit 1 }
