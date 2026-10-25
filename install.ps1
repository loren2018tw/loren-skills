#Requires -Version 7.2
<#
.SYNOPSIS
  將本倉庫的技能與 OpenCode agents 以檔案系統連結安裝到目標位置。

.DESCRIPTION
  語意與 install.sh 對齊。技能以目錄連接點（junction）安裝；OpenCode agent .md
  與輔助腳本以檔案符號連結（symlink）逐檔安裝到 OpenCode 設定根目錄的 agents/
  與 bin/。Windows 的檔案 symlink 需開啟 Developer Mode 或以管理員身分執行；
  本安裝器不採用 hardlink 或複本降級。

  需求：PowerShell 7.2 以上（pwsh）。Windows PowerShell 5.1 不支援；直接以
  5.1 執行時，#Requires 會立刻給出版本需求訊息。以 install.cmd 執行會先
  檢查 pwsh 是否存在，缺少時只顯示安裝指引，不做任何修改。

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -OnlyAgents
.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Skills geminiimage
#>
[CmdletBinding()]
param(
  [string]$Target,
  [Alias('Names')]
  [string[]]$Skills = @(),
  [string]$OpencodeDir,
  [Alias('Agents')]
  [switch]$OnlyAgents,
  [switch]$OnlySkills,
  [switch]$Uninstall,
  [switch]$Force,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# 輸出編碼：被 pipe／agent harness 捕捉時輸出 UTF-8；互動式主控台維持原代碼頁。
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ([Console]::IsOutputRedirected) {
  try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }
}

$Root     = [System.IO.Path]::GetFullPath($PSScriptRoot)
$RootFull = $Root.TrimEnd('\', '/')

$script:created = 0; $script:updated = 0; $script:unchanged = 0
$script:backed = 0; $script:pruned = 0; $script:removed = 0; $script:failed = 0

function Fail([string]$Message) {
  Write-Host "[錯誤] $Message" -ForegroundColor Red
  exit 1
}

function Expand-HomePath([string]$Path) {
  if (-not $Path) { return $Path }
  if ($Path -eq '~') { return $HOME }
  if ($Path.StartsWith('~/') -or $Path.StartsWith('~\')) {
    return Join-Path $HOME $Path.Substring(2)
  }
  return $Path
}

function Get-NormalizedPath([string]$Path) {
  $full = [System.IO.Path]::GetFullPath((Expand-HomePath $Path))
  $root = [System.IO.Path]::GetPathRoot($full)
  if ($full -ne $root) { $full = $full.TrimEnd('\', '/') }
  return $full
}

function Test-PathUnder([string]$Path, [string]$Base) {
  $p = Get-NormalizedPath $Path
  $b = Get-NormalizedPath $Base
  if ($p -ieq $b) { return $true }
  $sep = [System.IO.Path]::DirectorySeparatorChar
  $prefix = $b
  if (-not ($prefix.EndsWith('\') -or $prefix.EndsWith('/'))) { $prefix += $sep }
  return $p.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-LinkTarget($Path) {
  try {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  } catch {
    return $null
  }
  $target = $null
  if ($item.PSObject.Properties['Target'] -and $item.Target) {
    $target = [string]$item.Target
  }
  if (-not $target) {
    try {
      $resolved = [System.IO.File]::ResolveLinkTarget($Path, $false)
      if ($resolved) { $target = $resolved.FullName }
    } catch { }
  }
  if (-not $target) {
    try {
      $resolved = [System.IO.Directory]::ResolveLinkTarget($Path, $false)
      if ($resolved) { $target = $resolved.FullName }
    } catch { }
  }
  if (-not $target) { return $null }
  if (-not [System.IO.Path]::IsPathRooted($target)) {
    $target = Join-Path (Split-Path -Parent $Path) $target
  }
  return Get-NormalizedPath $target
}

function Remove-Link($Path) {
  $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
  if ($item -and ($item.Attributes -band [System.IO.FileAttributes]::Directory)) {
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

function New-FileLink([string]$Link, [string]$Src) {
  try {
    New-Item -ItemType SymbolicLink -Path $Link -Target $Src -ErrorAction Stop | Out-Null
  } catch {
    throw "建立檔案符號連結失敗：$Link。Windows 需開啟 Developer Mode 或以管理員身分執行；本安裝器不採用 hardlink／複本降級。"
  }
}

function New-ItemLink([string]$Kind, [string]$Link, [string]$Src) {
  if ($Kind -eq 'dir') { New-Junction $Link $Src } else { New-FileLink $Link $Src }
}

function Backup-AndInstall([string]$Label, [string]$Src, [string]$Link, [string]$Kind) {
  $bak = "$Link.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
  while ($null -ne (Get-Item -LiteralPath $bak -Force -ErrorAction SilentlyContinue)) {
    $bak += '-x'
  }
  if ($DryRun) {
    Write-Host "[預覽] 備份 $Label 後安裝（備份名：$(Split-Path -Leaf $bak)）"
    $script:backed++
    return
  }
  try {
    $item = Get-Item -LiteralPath $Link -Force -ErrorAction Stop
    if ($item.Attributes -band [System.IO.FileAttributes]::Directory) {
      if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        & cmd.exe /c move /Y "$Link" "$bak" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "移動目錄連結失敗：$Link" }
      } else {
        [System.IO.Directory]::Move($Link, $bak)
      }
    } else {
      [System.IO.File]::Move($Link, $bak)
    }
    New-ItemLink $Kind $Link $Src
  } catch {
    Write-Host "[失敗] 無法備份後安裝 $Label：$_" -ForegroundColor Red
    $script:failed++
    return
  }
  Write-Host "[備份後安裝] $Label（原項目 -> $(Split-Path -Leaf $bak)）"
  $script:backed++
}

function Install-OneItem([string]$Label, [string]$Src, [string]$Link, [string]$OwnedBase, [string]$Kind) {
  $item = $null
  try { $item = Get-Item -LiteralPath $Link -Force -ErrorAction Stop } catch { $item = $null }

  if ($item -and ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    $cur = Get-LinkTarget $Link
    if ($cur -and ((Get-NormalizedPath $cur) -ieq (Get-NormalizedPath $Src))) {
      Write-Host "[已最新] $Label"
      $script:unchanged++
      return
    }
    if ($cur -and (Test-PathUnder $cur $OwnedBase)) {
      if ($DryRun) { Write-Host "[預覽] 重指 $Label -> $Src"; $script:updated++; return }
      try {
        Remove-Link $Link
        New-ItemLink $Kind $Link $Src
      } catch {
        Write-Host "[失敗] 無法重指 $Label：$_" -ForegroundColor Red
        $script:failed++
        return
      }
      Write-Host "[重指] $Label -> $Src"
      $script:updated++
      return
    }
    if (-not $Force) {
      Write-Host "[跳過] $Label：目標已有非本倉庫的連結，未覆蓋（可加 -Force 先備份再安裝）" -ForegroundColor Yellow
      $script:failed++
      return
    }
    Backup-AndInstall $Label $Src $Link $Kind
    return
  }

  if ($item) {
    if (-not $Force) {
      Write-Host "[跳過] $Label：目標已有實體項目，未覆蓋（可加 -Force 先備份再安裝）" -ForegroundColor Yellow
      $script:failed++
      return
    }
    Backup-AndInstall $Label $Src $Link $Kind
    return
  }

  if ($DryRun) { Write-Host "[預覽] 新增 $Label -> $Src"; $script:created++; return }
  try { New-ItemLink $Kind $Link $Src } catch {
    Write-Host "[失敗] 無法建立連結 $Label：$_" -ForegroundColor Red
    $script:failed++
    return
  }
  Write-Host "[安裝] $Label -> $Src"
  $script:created++
}

function Ensure-Dir([string]$Dir, [string]$Label) {
  if (Test-Path -LiteralPath $Dir -PathType Container) { return }
  if (Test-Path -LiteralPath $Dir) { Fail "$Label 不是目錄：$Dir" }
  if ($DryRun) {
    Write-Host "[預覽] 建立 $Label $Dir"
    return
  }
  try {
    New-Item -ItemType Directory -Path $Dir -Force -ErrorAction Stop | Out-Null
  } catch {
    Fail "無法建立 $Label：$Dir"
  }
}

function Get-TargetLinks([string]$Dir) {
  if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { return @() }
  return @(Get-ChildItem -LiteralPath $Dir -Force -ErrorAction Stop |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
}

function Invoke-Prune([string]$Dir, [string]$Base, [string[]]$Expected) {
  foreach ($l in Get-TargetLinks $Dir) {
    if ($Expected -contains $l.Name) { continue }
    $cur = Get-LinkTarget $l.FullName
    if (-not $cur) { continue }
    if (-not (Test-PathUnder $cur $Base)) { continue }
    if ($DryRun) { Write-Host "[預覽] 清除陳舊連結 $($l.Name)"; $script:pruned++; continue }
    try {
      Remove-Link $l.FullName
      Write-Host "[清除陳舊] $($l.Name)"
      $script:pruned++
    } catch {
      Write-Host "[失敗] 無法清除陳舊連結 $($l.Name)：$_" -ForegroundColor Red
      $script:failed++
    }
  }
}

function Remove-OwnedLink([string]$Link, [string]$Label) {
  if ($DryRun) { Write-Host "[預覽] 移除連結 $Label"; $script:removed++; return }
  try {
    Remove-Link $Link
    Write-Host "[移除] $Label"
    $script:removed++
  } catch {
    Write-Host "[失敗] 無法移除連結 $Label：$_" -ForegroundColor Red
    $script:failed++
  }
}

function Invoke-UninstallAll([string]$Dir, [string]$Base) {
  foreach ($l in Get-TargetLinks $Dir) {
    $cur = Get-LinkTarget $l.FullName
    if (-not $cur) { continue }
    if (-not (Test-PathUnder $cur $Base)) { continue }
    Remove-OwnedLink $l.FullName $l.Name
  }
}

function Remove-Named([string]$Link, [string]$Base, [string]$Label) {
  $item = Get-Item -LiteralPath $Link -Force -ErrorAction SilentlyContinue
  if (-not $item) { return }
  if (-not ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    Write-Host "[跳過] ${Label}：目標是實體項目，未移除" -ForegroundColor Yellow
    return
  }
  $cur = Get-LinkTarget $Link
  if (-not $cur -or -not (Test-PathUnder $cur $Base)) {
    Write-Host "[跳過] ${Label}：不是本倉庫的連結，未移除" -ForegroundColor Yellow
    return
  }
  Remove-OwnedLink $Link $Label
}

function Count-OwnedLinks([string]$Dir, [string]$Base) {
  $count = 0
  foreach ($l in Get-TargetLinks $Dir) {
    $cur = Get-LinkTarget $l.FullName
    if ($cur -and (Test-PathUnder $cur $Base)) { $count++ }
  }
  return $count
}

# ---- 選取類別 ---------------------------------------------------------------
if (-not $OnlyAgents -and -not $OnlySkills) {
  $selAgents = $true
  $selSkills = $true
} else {
  $selAgents = [bool]$OnlyAgents
  $selSkills = [bool]$OnlySkills
}

# ---- 目標路徑 ---------------------------------------------------------------
if (-not $Target) { $Target = Join-Path $HOME '.agents' 'skills' }
$Target = Get-NormalizedPath $Target

$AgentSource = Join-Path $Root 'opencode' 'agents'
$BinSource   = Join-Path $Root 'opencode' 'bin'

if ($selSkills) {
  if (Test-PathUnder $Target $RootFull) { Fail "目標技能庫不能位於本倉庫內：$Target" }
  if ((Test-Path -LiteralPath $Target) -and -not (Test-Path -LiteralPath $Target -PathType Container)) {
    Fail "目標技能庫不是目錄：$Target"
  }
}

$AgentsTarget = ''
$BinTarget = ''
if ($selAgents) {
  if (-not $OpencodeDir) {
    if ($env:OPENCODE_CONFIG_DIR) {
      $OpencodeDir = $env:OPENCODE_CONFIG_DIR
    } elseif ($env:XDG_CONFIG_HOME) {
      $OpencodeDir = Join-Path $env:XDG_CONFIG_HOME 'opencode'
    } else {
      $OpencodeDir = Join-Path $HOME '.config' 'opencode'
    }
  }
  $OpencodeDir = Get-NormalizedPath $OpencodeDir
  if (Test-PathUnder $OpencodeDir $RootFull) {
    Fail "OpenCode 設定根目錄不能位於本倉庫內：$OpencodeDir"
  }
  if ((Test-Path -LiteralPath $OpencodeDir) -and -not (Test-Path -LiteralPath $OpencodeDir -PathType Container)) {
    Fail "OpenCode 設定根目錄不是目錄：$OpencodeDir"
  }
  $AgentsTarget = Join-Path $OpencodeDir 'agents'
  $BinTarget = Join-Path $OpencodeDir 'bin'
  foreach ($d in @($AgentsTarget, $BinTarget)) {
    if ((Test-Path -LiteralPath $d) -and -not (Test-Path -LiteralPath $d -PathType Container)) {
      Fail "OpenCode 目標不是目錄：$d"
    }
  }
  if ($selSkills -and $Target -ieq $OpencodeDir) {
    Fail "技能目標與 OpenCode 設定根目錄不能相同：$Target"
  }
}

# ---- 項目偵測 ---------------------------------------------------------------
$skillNames = @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction Stop |
  Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
  ForEach-Object { $_.Name })

$agentNames = @()
$agentFiles = @()
if (Test-Path -LiteralPath $AgentSource -PathType Container) {
  $agentItems = @(Get-ChildItem -LiteralPath $AgentSource -Filter '*.md' -File -ErrorAction Stop)
  $agentNames = @($agentItems | ForEach-Object { $_.BaseName })
  $agentFiles = @($agentItems | ForEach-Object { $_.Name })
}

$binNames = @()
if (Test-Path -LiteralPath $BinSource -PathType Container) {
  $binNames = @(Get-ChildItem -LiteralPath $BinSource -Filter '*.py' -File -ErrorAction Stop |
    ForEach-Object { $_.Name })
}

# ---- 選取項目 ---------------------------------------------------------------
$names = @($Skills)
$selectedSkills = @()
$selectedAgents = @()
$selectedBins = @()
$fullSkills = $false
$fullAgents = $false

if ($names.Count -gt 0) {
  foreach ($n in $names) {
    $isSkill = $skillNames -contains $n
    $isAgent = $agentNames -contains $n
    $isBin = $binNames -contains $n
    if (-not ($isSkill -or $isAgent -or $isBin)) {
      Fail "不是可安裝的技能、agent 或輔助腳本：$n（技能：$($skillNames -join '、')；agents：$($agentNames -join '、')；腳本：$($binNames -join '、')）"
    }
    if ($isSkill -and $isAgent) { Fail "名稱同時對應技能與 agent，無法判定：$n" }
    if ($isSkill -and -not $selSkills) { Fail "目前只處理 OpenCode agents，不能選技能：$n" }
    if ($isAgent -and -not $selAgents) { Fail "目前只處理技能，不能選 agent：$n" }
    if ($isBin) {
      if (-not $selAgents) { Fail "目前只處理技能，不能選輔助腳本：$n" }
      if (-not $Uninstall) { Fail "輔助腳本會隨 agent 一併安裝；安裝時請指定 agent 名稱，不要指定 $n" }
    }
  }

  if ($selSkills) {
    $selectedSkills = @($skillNames | Where-Object { $names -contains $_ })
  }
  if ($selAgents) {
    $selectedAgents = @($agentNames | Where-Object { $names -contains $_ })
    if (-not $Uninstall -and $selectedAgents.Count -gt 0) {
      $selectedBins = @($binNames)
    } else {
      $selectedBins = @($binNames | Where-Object { $names -contains $_ })
    }
  }
} else {
  if ($selSkills) {
    if ($skillNames.Count -eq 0) { Fail '根目錄下找不到任何含 SKILL.md 的技能目錄' }
    $fullSkills = $true
    $selectedSkills = @($skillNames)
  }
  if ($selAgents) {
    if ($agentNames.Count -eq 0) { Fail 'opencode/agents 下找不到任何 .md agent' }
    $fullAgents = $true
    $selectedAgents = @($agentNames)
    $selectedBins = @($binNames)
  }
}

if ($selectedAgents.Count -gt 0 -and $binNames.Count -eq 0) {
  Fail '找到 OpenCode agent，但 opencode/bin 下沒有 .py 輔助腳本'
}

# ---- 主流程 -----------------------------------------------------------------
Write-Host "[資訊] 本倉庫：$Root"
if ($selSkills) { Write-Host "[資訊] 目標技能庫：$Target" }
if ($selAgents) { Write-Host "[資訊] OpenCode 設定根目錄：$OpencodeDir" }
if ($DryRun) { Write-Host '[資訊] dry-run：只預覽，不做任何修改' }

if ($Uninstall) {
  if ($selSkills) {
    if ($names.Count -eq 0) {
      Invoke-UninstallAll $Target $RootFull
    } else {
      foreach ($s in $selectedSkills) {
        Remove-Named (Join-Path $Target $s) $RootFull "技能 $s"
      }
    }
  }

  if ($selAgents) {
    if ($names.Count -eq 0) {
      Invoke-UninstallAll $AgentsTarget $AgentSource
      Invoke-UninstallAll $BinTarget $BinSource
    } else {
      $removedAgent = $false
      foreach ($a in $selectedAgents) {
        Remove-Named (Join-Path $AgentsTarget "$a.md") $AgentSource "agent $a"
        $removedAgent = $true
      }
      foreach ($b in $selectedBins) {
        Remove-Named (Join-Path $BinTarget $b) $BinSource "腳本 $b"
      }
      if ($removedAgent -and (Count-OwnedLinks $AgentsTarget $AgentSource) -eq 0) {
        Invoke-UninstallAll $BinTarget $BinSource
      }
    }
  }

  Write-Host ("完成：移除 {0}、失敗 {1}" -f $script:removed, $script:failed)
  if ($script:failed -gt 0) { exit 1 }
  exit 0
}

if ($selSkills -and $selectedSkills.Count -gt 0) { Ensure-Dir $Target '目標技能庫' }
if ($selAgents -and $selectedAgents.Count -gt 0) {
  Ensure-Dir $AgentsTarget '目標 agent 目錄'
  Ensure-Dir $BinTarget '目標腳本目錄'
}

if ($fullSkills) { Invoke-Prune $Target $RootFull $skillNames }
if ($fullAgents) {
  Invoke-Prune $AgentsTarget $AgentSource $agentFiles
  Invoke-Prune $BinTarget $BinSource $binNames
}

foreach ($s in $selectedSkills) {
  Install-OneItem "技能 $s" (Join-Path $Root $s) (Join-Path $Target $s) $RootFull 'dir'
}
foreach ($a in $selectedAgents) {
  Install-OneItem "agent $a" (Join-Path $AgentSource "$a.md") (Join-Path $AgentsTarget "$a.md") $AgentSource 'file'
}
foreach ($b in $selectedBins) {
  Install-OneItem "腳本 $b" (Join-Path $BinSource $b) (Join-Path $BinTarget $b) $BinSource 'file'
}

Write-Host ("完成：新增 {0}、重指 {1}、已最新 {2}、備份 {3}、清除陳舊 {4}、失敗 {5}" -f `
  $script:created, $script:updated, $script:unchanged, $script:backed, $script:pruned, $script:failed)

if (-not $DryRun -and ($script:created + $script:updated + $script:backed) -gt 0) {
  Write-Host '提示：連結即時生效；若 OpenCode 有技能或 agent 清單快取，重新載入即可看到。'
}

if ($script:failed -gt 0) { exit 1 }
