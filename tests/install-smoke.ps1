#Requires -Version 7.2
# Windows（pwsh 7.2+）junction 生命週期 smoke：安裝 → 冪等 → 實體項目保護 → 卸載 → 外來項目完好。
# 可本機執行；CI 亦會呼叫。
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tempRoot = [System.IO.Path]::GetTempPath()
$stamp = [guid]::NewGuid().ToString('N')
$target = Join-Path $tempRoot "loren-skills-smoke-$stamp"
$guardTarget = Join-Path $tempRoot "loren-skills-guard-$stamp"
$foreignReal = Join-Path $tempRoot "loren-skills-foreign-$stamp"
$script:fail = 0

function Ok([string]$Message) { Write-Host "[OK]   $Message" }
function Bad([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; $script:fail++ }

function Remove-TempTree([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return }
  Get-ChildItem -LiteralPath $Path -Force | ForEach-Object {
    if ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
      & cmd.exe /c rmdir "$($_.FullName)" | Out-Null
    } else {
      Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
  Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
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

  # ---- 外來項目：普通複本目錄＋指向倉庫外的 junction ----
  New-Item -ItemType Directory -Path $target -Force | Out-Null
  $foreignCopy = Join-Path $target 'foreign-copy'
  New-Item -ItemType Directory -Path $foreignCopy -Force | Out-Null
  New-Item -ItemType Directory -Path $foreignReal -Force | Out-Null
  $foreignLink = Join-Path $target 'foreign-link'
  New-Item -ItemType Junction -Path $foreignLink -Target $foreignReal | Out-Null

  # ---- 1) 安裝 ----
  & $installPs1 -Target $target | Out-Null
  $missing = @($skills | Where-Object { -not (Test-Path -LiteralPath (Join-Path $target $_)) })
  if ($missing.Count -eq 0) { Ok '安裝後所有技能連結存在' } else { Bad "缺連結：$($missing -join '、')" }
  $sample = $skills[0]
  $sampleLink = Join-Path $target $sample
  $item = Get-Item -LiteralPath $sampleLink -Force
  if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    Ok "$sample 是連結"
  } else {
    Bad "$sample 不是連結"
  }
  $resolved = [System.IO.Directory]::ResolveLinkTarget($sampleLink, $false)
  $expect = (Join-Path $root $sample).TrimEnd('\')
  if ($resolved -and $resolved.FullName.TrimEnd('\') -ieq $expect) {
    Ok "$sample 連結指向正確"
  } else {
    Bad "$sample 連結指向錯誤（預期 $expect）"
  }

  # ---- 2) 冪等 ----
  $out2 = & $installPs1 -Target $target 6>&1 | Out-String
  if ($out2 -match '新增 0' -and $out2 -match '已最新') {
    Ok '第二次安裝冪等（新增 0、已最新）'
  } else {
    Bad "第二次安裝非冪等：$out2"
  }

  # ---- 3) 實體項目保護（無 -Force 跳過；-Force 備份後安裝）----
  New-Item -ItemType Directory -Path (Join-Path $guardTarget $sample) -Force | Out-Null
  Set-Content -LiteralPath (Join-Path $guardTarget "$sample\keep.txt") -Value 'keep'
  $null = & $installPs1 -Target $guardTarget -Skills $sample 6>&1
  $g = Get-Item -LiteralPath (Join-Path $guardTarget $sample) -Force
  if ((-not ($g.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) -and
      (Test-Path -LiteralPath (Join-Path $guardTarget "$sample\keep.txt"))) {
    Ok '無 -Force 時實體項目未被覆蓋'
  } else {
    Bad '實體項目被覆蓋了'
  }
  $outForce = & $installPs1 -Target $guardTarget -Skills $sample -Force 6>&1 | Out-String
  $g2 = Get-Item -LiteralPath (Join-Path $guardTarget $sample) -Force
  $bak = Get-ChildItem -LiteralPath $guardTarget -Force | Where-Object { $_.Name -like "$sample.bak-*" }
  if (($g2.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -and $bak) {
    Ok '-Force 備份後安裝連結'
  } else {
    Bad "-Force 行為不符：$outForce"
  }

  # ---- 4) 卸載：本倉庫連結全移除，外來項目完好 ----
  & $installPs1 -Target $target -Uninstall | Out-Null
  $leftover = @($skills | Where-Object { Test-Path -LiteralPath (Join-Path $target $_) })
  if ($leftover.Count -eq 0) { Ok '卸載後技能連結全數移除' } else { Bad "卸載後殘留：$($leftover -join '、')" }
  if (Test-Path -LiteralPath $foreignCopy) { Ok '外來複本未被動到' } else { Bad '外來複本被刪' }
  $fl = Get-Item -LiteralPath $foreignLink -Force -ErrorAction SilentlyContinue
  if ($fl -and ($fl.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    Ok '外來連結未被動到'
  } else {
    Bad '外來連結被刪或已非連結'
  }
  $linkCount = @(Get-ChildItem -LiteralPath $target -Force |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }).Count
  if ($linkCount -eq 1) { Ok '卸載後目標僅剩外來連結' } else { Bad "卸載後連結數為 $linkCount（預期 1）" }
}
finally {
  Remove-TempTree $target
  Remove-TempTree $guardTarget
  Remove-TempTree $foreignReal
}

if ($script:fail -eq 0) {
  Write-Host 'Windows smoke 全部通過'
} else {
  Write-Host "Windows smoke 失敗：$($script:fail) 項" -ForegroundColor Red
  exit 1
}
