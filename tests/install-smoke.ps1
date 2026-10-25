#Requires -Version 7.2
# Windows（pwsh 7.2+）生命週期 smoke：技能 junction＋agent／bin 檔案 symlink
# → 冪等 → 外來項目不動 → 名稱選取 → 清除陳舊 → 卸載 → 目標乾淨。
# 可本機執行；CI 亦會呼叫。檔案 symlink 需 Developer Mode 或管理員權限。
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tempRoot = [System.IO.Path]::GetTempPath()
$stamp = [guid]::NewGuid().ToString('N')
$base = Join-Path $tempRoot "loren-skills-smoke-$stamp"
$target = Join-Path $base 'skills'
$opencode = Join-Path $base 'opencode'
$outside = Join-Path $base 'outside'
$script:fail = 0

function Ok([string]$Message) { Write-Host "[OK]   $Message" }
function Bad([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; $script:fail++ }

function Remove-TempTree([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
  if (-not $item) { return }
  if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    if ($item.Attributes -band [System.IO.FileAttributes]::Directory) {
      & cmd.exe /c rmdir "$Path" | Out-Null
    } else {
      Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
    return
  }
  if ($item.Attributes -band [System.IO.FileAttributes]::Directory) {
    Get-ChildItem -LiteralPath $Path -Force | ForEach-Object { Remove-TempTree $_.FullName }
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
  } else {
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
  }
}

function Invoke-Installer([hashtable]$Arguments) {
  $global:LASTEXITCODE = 0
  $output = & $installPs1 @Arguments 6>&1 | Out-String
  return [pscustomobject]@{ Code = $LASTEXITCODE; Output = $output }
}

function Test-LinkTarget([string]$Link, [string]$Src, [bool]$Directory = $false) {
  $item = Get-Item -LiteralPath $Link -Force -ErrorAction SilentlyContinue
  if (-not $item -or -not ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    return $false
  }
  try {
    $resolved = if ($Directory) {
      [System.IO.Directory]::ResolveLinkTarget($Link, $false)
    } else {
      [System.IO.File]::ResolveLinkTarget($Link, $false)
    }
  } catch {
    return $false
  }
  return ($resolved -and ($resolved.FullName -ieq $Src))
}

function Check-Link([string]$Link, [string]$Src, [string]$Label, [bool]$Directory = $false) {
  if (Test-LinkTarget $Link $Src $Directory) { Ok "$Label 連結指向正確" }
  else { Bad "$Label 未建立連結或指向錯誤" }
}

function Check-NoLink([string]$Link, [string]$Label) {
  $item = Get-Item -LiteralPath $Link -Force -ErrorAction SilentlyContinue
  if (-not $item) { Ok "$Label 已移除"; return }
  if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { Bad "$Label 仍存在" }
  else { Bad "$Label 變成實體項目" }
}

function Count-LinksIn([string]$Dir) {
  if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { return 0 }
  $links = @(Get-ChildItem -LiteralPath $Dir -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
  return $links.Count
}

try {
  # ---- 0) install.ps1 具 UTF-8 BOM ----
  $bytes = [System.IO.File]::ReadAllBytes((Join-Path $root 'install.ps1'))
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Ok 'install.ps1 具 UTF-8 BOM'
  } else {
    Bad 'install.ps1 缺 UTF-8 BOM'
  }

  $installPs1 = Join-Path $root 'install.ps1'
  $skills = @(Get-ChildItem -LiteralPath $root -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
    ForEach-Object { $_.Name })
  if ($skills.Count -gt 0) { Ok "偵測到 $($skills.Count) 個技能" } else { Bad '找不到任何技能'; throw '無法繼續' }

  $agentSource = Join-Path $root 'opencode' 'agents'
  $binSource = Join-Path $root 'opencode' 'bin'
  $agents = @(Get-ChildItem -LiteralPath $agentSource -Filter '*.md' -File)
  $bins = @(Get-ChildItem -LiteralPath $binSource -Filter '*.py' -File)
  if ($agents.Count -gt 0) { Ok "偵測到 $($agents.Count) 個 OpenCode agent" } else { Bad '找不到 OpenCode agents'; throw '無法繼續' }
  if ($bins.Count -gt 0) { Ok "偵測到 $($bins.Count) 個輔助腳本" } else { Bad '找不到輔助腳本'; throw '無法繼續' }

  # ---- 外來項目：實體檔案、目錄 junction、檔案 symlink ----
  New-Item -ItemType Directory -Path $target -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $target 'foreign-copy') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $opencode 'agents') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $opencode 'bin') -Force | Out-Null
  New-Item -ItemType Directory -Path $outside -Force | Out-Null
  Set-Content -LiteralPath (Join-Path $outside 'keep.txt') -Value 'outside'
  Set-Content -LiteralPath (Join-Path $opencode 'agents\remote.md') -Value 'remote'

  $foreignDirLink = Join-Path $target 'foreign-link'
  New-Item -ItemType Junction -Path $foreignDirLink -Target $outside | Out-Null
  $foreignAgentLink = Join-Path $opencode 'agents\foreign-link.md'
  $foreignBinLink = Join-Path $opencode 'bin\foreign-link.py'
  New-Item -ItemType SymbolicLink -Path $foreignAgentLink -Target (Join-Path $outside 'keep.txt') | Out-Null
  New-Item -ItemType SymbolicLink -Path $foreignBinLink -Target (Join-Path $outside 'keep.txt') | Out-Null

  # ---- 1) 全量安裝 ----
  $r = Invoke-Installer @{ Target = $target; OpencodeDir = $opencode }
  if ($r.Code -ne 0) { Bad "全量安裝失敗：$($r.Output)"; throw '無法繼續' }

  foreach ($s in $skills) {
    Check-Link (Join-Path $target $s) (Join-Path $root $s) "技能 $s" $true
  }
  foreach ($a in $agents) {
    Check-Link (Join-Path $opencode "agents\$($a.Name)") $a.FullName "agent $($a.Name)"
  }
  foreach ($b in $bins) {
    Check-Link (Join-Path $opencode "bin\$($b.Name)") $b.FullName "腳本 $($b.Name)"
  }

  if ((Get-Content -Raw -LiteralPath (Join-Path $opencode 'agents\remote.md')).Trim() -eq 'remote') {
    Ok '既有實體 agent（remote.md）未被動到'
  } else {
    Bad '既有實體 agent 被動到'
  }
  Check-Link $foreignAgentLink (Join-Path $outside 'keep.txt') 'agents 外來連結'
  Check-Link $foreignBinLink (Join-Path $outside 'keep.txt') 'bin 外來連結'
  if ((Test-Path -LiteralPath (Join-Path $target 'foreign-copy')) -and (Test-LinkTarget $foreignDirLink $outside $true)) {
    Ok '技能目標的外來項目未被動到'
  } else {
    Bad '技能目標的外來項目被動到'
  }

  # ---- 2) 冪等 ----
  $r = Invoke-Installer @{ Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0 -and $r.Output -match '新增 0' -and $r.Output -match '已最新') {
    Ok '第二次安裝冪等（新增 0、已最新）'
  } else {
    Bad "第二次安裝非冪等：$($r.Output)"
  }

  # ---- 3) 清除陳舊連結 ----
  New-Item -ItemType SymbolicLink -Path (Join-Path $opencode 'agents\gone.md') -Target (Join-Path $agentSource 'gone.md') | Out-Null
  New-Item -ItemType SymbolicLink -Path (Join-Path $opencode 'bin\gone.py') -Target (Join-Path $binSource 'gone.py') | Out-Null
  $r = Invoke-Installer @{ Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0) { Ok '清除陳舊安裝成功' } else { Bad "清除陳舊安裝失敗：$($r.Output)" }
  Check-NoLink (Join-Path $opencode 'agents\gone.md') '陳舊 agent 連結'
  Check-NoLink (Join-Path $opencode 'bin\gone.py') '陳舊腳本連結'
  Check-Link $foreignAgentLink (Join-Path $outside 'keep.txt') '清除陳舊後的 agents 外來連結'

  # ---- 4) 名稱卸載：最後一個 agent 移除時一併清 bin ----
  $r = Invoke-Installer @{ Uninstall = $true; Skills = @('geminiimage'); Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0) { Ok '名稱卸載 agent 成功' } else { Bad "名稱卸載 agent 失敗：$($r.Output)" }
  Check-NoLink (Join-Path $opencode 'agents\geminiimage.md') 'agent geminiimage'
  Check-Link (Join-Path $opencode 'agents\gptimage.md') (Join-Path $agentSource 'gptimage.md') 'agent gptimage 仍在'
  Check-Link (Join-Path $opencode 'bin\geminiimage.py') (Join-Path $binSource 'geminiimage.py') '還有 agent 時保留腳本'

  $r = Invoke-Installer @{ Uninstall = $true; Skills = @('gptimage'); Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0) { Ok '卸載最後一個 agent 成功' } else { Bad "卸載最後一個 agent 失敗：$($r.Output)" }
  Check-NoLink (Join-Path $opencode 'agents\gptimage.md') 'agent gptimage'
  Check-NoLink (Join-Path $opencode 'bin\geminiimage.py') '沒有 agent 時移除腳本'
  Check-NoLink (Join-Path $opencode 'bin\gptimage.py') '沒有 agent 時移除腳本'

  # ---- 5) 類別卸載：-OnlyAgents 不動技能；-OnlySkills 只動技能 ----
  $r = Invoke-Installer @{ Target = $target; OpencodeDir = $opencode }
  if ($r.Code -ne 0) { Bad "重新安裝失敗：$($r.Output)"; throw '無法繼續' }
  $r = Invoke-Installer @{ Uninstall = $true; OnlyAgents = $true; Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0) { Ok '卸載 agents 成功' } else { Bad "卸載 agents 失敗：$($r.Output)" }
  Check-NoLink (Join-Path $opencode 'agents\geminiimage.md') '卸載 agents 後的 agent'
  Check-NoLink (Join-Path $opencode 'bin\geminiimage.py') '卸載 agents 後的腳本'
  Check-Link (Join-Path $target 'who-is-loren') (Join-Path $root 'who-is-loren') '卸載 agents 後技能仍在' $true

  $r = Invoke-Installer @{ Uninstall = $true; OnlySkills = $true; Target = $target; OpencodeDir = $opencode }
  if ($r.Code -eq 0) { Ok '卸載技能成功' } else { Bad "卸載技能失敗：$($r.Output)" }
  Check-NoLink (Join-Path $target 'who-is-loren') '卸載技能後的技能'
  Check-Link $foreignAgentLink (Join-Path $outside 'keep.txt') '全數卸載後 agents 外來連結仍在'
  Check-Link $foreignBinLink (Join-Path $outside 'keep.txt') '全數卸載後 bin 外來連結仍在'
  if ((Get-Content -Raw -LiteralPath (Join-Path $opencode 'agents\remote.md')).Trim() -eq 'remote') {
    Ok '全數卸載後實體 agent 仍在'
  } else {
    Bad '全數卸載後實體 agent 消失'
  }

  $n = (Count-LinksIn (Join-Path $opencode 'agents')) + (Count-LinksIn (Join-Path $opencode 'bin'))
  if ($n -eq 2) { Ok '卸載後 OpenCode 目標僅剩 2 個外來連結' } else { Bad "卸載後 OpenCode 連結數為 $n（預期 2）" }
  $n = Count-LinksIn $target
  if ($n -eq 1) { Ok '卸載後技能目標僅剩外來連結' } else { Bad "卸載後技能連結數為 $n（預期 1）" }

  # ---- 6) 只安裝技能：不建立 OpenCode 目錄 ----
  $target2 = Join-Path $base 'skills-only'
  $opencode2 = Join-Path $base 'opencode-skills-only'
  $r = Invoke-Installer @{ OnlySkills = $true; Target = $target2; OpencodeDir = $opencode2 }
  if ($r.Code -eq 0) { Ok '只安裝技能成功' } else { Bad "只安裝技能失敗：$($r.Output)" }
  Check-Link (Join-Path $target2 'who-is-loren') (Join-Path $root 'who-is-loren') '只安裝技能' $true
  if (Test-Path -LiteralPath $opencode2) { Bad '只安裝技能卻建立了 OpenCode 目錄' } else { Ok '只安裝技能未建立 OpenCode 目錄' }
  $null = Invoke-Installer @{ Uninstall = $true; OnlySkills = $true; Target = $target2; OpencodeDir = $opencode2 }

  # ---- 7) 只安裝 agents：不建立技能目錄；指定名稱只裝該 agent ----
  $target3 = Join-Path $base 'skills-agents-only'
  $opencode3 = Join-Path $base 'opencode-agents-only'
  $r = Invoke-Installer @{ OnlyAgents = $true; Target = $target3; OpencodeDir = $opencode3 }
  if ($r.Code -eq 0) { Ok '只安裝 agents 成功' } else { Bad "只安裝 agents 失敗：$($r.Output)" }
  Check-Link (Join-Path $opencode3 'agents\geminiimage.md') (Join-Path $agentSource 'geminiimage.md') '只安裝 agents'
  Check-Link (Join-Path $opencode3 'bin\geminiimage.py') (Join-Path $binSource 'geminiimage.py') '只安裝 agents 的腳本'
  if (Test-Path -LiteralPath $target3) { Bad '只安裝 agents 卻建立了技能目錄' } else { Ok '只安裝 agents 未建立技能目錄' }
  $null = Invoke-Installer @{ Uninstall = $true; OnlyAgents = $true; Target = $target3; OpencodeDir = $opencode3 }

  $target4 = Join-Path $base 'skills-named-agent'
  $opencode4 = Join-Path $base 'opencode-named-agent'
  $r = Invoke-Installer @{ Skills = @('geminiimage'); Target = $target4; OpencodeDir = $opencode4 }
  if ($r.Code -eq 0) { Ok '指定名稱安裝 agent 成功' } else { Bad "指定名稱安裝 agent 失敗：$($r.Output)" }
  Check-Link (Join-Path $opencode4 'agents\geminiimage.md') (Join-Path $agentSource 'geminiimage.md') '指定名稱安裝 agent'
  Check-NoLink (Join-Path $opencode4 'agents\gptimage.md') '未指定的 agent'
  Check-Link (Join-Path $opencode4 'bin\geminiimage.py') (Join-Path $binSource 'geminiimage.py') '指定 agent 的腳本'
  Check-Link (Join-Path $opencode4 'bin\gptimage.py') (Join-Path $binSource 'gptimage.py') '指定 agent 仍安裝共用腳本集'
  if (Test-Path -LiteralPath $target4) { Bad '指定 agent 卻建立了技能目錄' } else { Ok '指定 agent 未建立技能目錄' }
  $null = Invoke-Installer @{ Uninstall = $true; OnlyAgents = $true; Target = $target4; OpencodeDir = $opencode4 }

  # ---- 8) dry-run：只預覽，不建立任何目錄 ----
  $target5 = Join-Path $base 'skills-dry'
  $opencode5 = Join-Path $base 'opencode-dry'
  $r = Invoke-Installer @{ DryRun = $true; Target = $target5; OpencodeDir = $opencode5 }
  if ($r.Code -eq 0 -and $r.Output -match '\[預覽\]') { Ok 'dry-run 有預覽輸出' } else { Bad "dry-run 輸出不符：$($r.Output)" }
  if ((Test-Path -LiteralPath $target5) -or (Test-Path -LiteralPath $opencode5)) { Bad 'dry-run 建立了目錄' } else { Ok 'dry-run 未建立任何目錄' }

  # ---- 9) 外來同名連結：無 -Force 跳過；-Force 備份後連結 ----
  $target6 = Join-Path $base 'skills-conflict'
  $opencode6 = Join-Path $base 'opencode-conflict'
  New-Item -ItemType Directory -Path (Join-Path $opencode6 'agents') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $opencode6 'bin') -Force | Out-Null
  $foreignAgent = Join-Path $outside 'foreign-agent.md'
  Set-Content -LiteralPath $foreignAgent -Value 'foreign-agent'
  $conflictLink = Join-Path $opencode6 'agents\geminiimage.md'
  New-Item -ItemType SymbolicLink -Path $conflictLink -Target $foreignAgent | Out-Null

  $r = Invoke-Installer @{ Skills = @('geminiimage'); Target = $target6; OpencodeDir = $opencode6 }
  if ($r.Code -ne 0) { Ok '外來同名連結被擋下' } else { Bad '外來同名連結未被擋下' }
  Check-Link $conflictLink $foreignAgent '外來同名連結'

  $r = Invoke-Installer @{ Skills = @('geminiimage'); Force = $true; Target = $target6; OpencodeDir = $opencode6 }
  if ($r.Code -eq 0) { Ok '-Force 安裝成功' } else { Bad "-Force 安裝失敗：$($r.Output)" }
  Check-Link $conflictLink (Join-Path $agentSource 'geminiimage.md') '-Force 後 agent 連結'
  $bak = Get-ChildItem -LiteralPath (Join-Path $opencode6 'agents') -Force -Filter 'geminiimage.md.bak-*' | Select-Object -First 1
  if ($bak -and (Test-LinkTarget $bak.FullName $foreignAgent)) {
    Ok '-Force 備份了原外來連結'
  } else {
    Bad '-Force 未正確備份原外來連結'
  }
  $null = Invoke-Installer @{ Uninstall = $true; OnlyAgents = $true; Target = $target6; OpencodeDir = $opencode6 }
}
finally {
  Remove-TempTree $base
}

if ($script:fail -eq 0) {
  Write-Host 'Windows smoke 全部通過'
} else {
  Write-Host "Windows smoke 失敗：$($script:fail) 項" -ForegroundColor Red
  exit 1
}
