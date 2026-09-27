# =============================================================================
#  ES12F 本地化固件 —— 独立校验脚本（不依赖 flash.ps1）
#
#  读回整片 1MB flash，逐项核对：
#    · 0x000000  eboot 引导程序（E9 魔数 + 入口地址）
#    · 0x001000  应用镜像头（E9 魔数 + 入口地址）
#    · 0x000000..len(firmware)  与 release\ES12F_Local_firmware.bin 是否逐字节一致
#    · 0x0FB000  配置扇区状态（已配网 / 空白 = 首次上电进配网热点）
#    · 全片 SHA256
#
#  用法：  .\verify.ps1 -Port COM3
# =============================================================================
[CmdletBinding()]
param(
  [string]$Port = 'COM3',
  [int]$Baud = 460800,
  [string]$OutDir
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) { $OutDir = Join-Path $Root 'release' }

$fwBin = Join-Path $OutDir 'ES12F_Local_firmware.bin'
if (-not (Test-Path $fwBin)) { throw "找不到 $fwBin（先运行 tools\make_images.py）" }
$fw = [System.IO.File]::ReadAllBytes($fwBin)

$tmp = Join-Path $env:TEMP ("es12f_readback_{0}.bin" -f (Get-Random))
Write-Host "读取整片 1MB ..." -ForegroundColor Yellow
& python -m esptool --port $Port --baud $Baud --before no-reset --after no-reset read-flash 0x0 0x100000 $tmp
if ($LASTEXITCODE -ne 0) { throw "read-flash 失败 (exit $LASTEXITCODE)" }

$dump = [System.IO.File]::ReadAllBytes($tmp)
if ($dump.Length -ne 0x100000) { throw "读回长度异常: $($dump.Length)" }

function Hex([byte[]]$b, [int]$off, [int]$n) {
  ($b[$off..($off + $n - 1)] | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
}
function Sha256Bytes([byte[]]$b) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  ($sha.ComputeHash($b) | ForEach-Object { '{0:X2}' -f $_ }) -join ''
}

$ok = $true
Write-Host ""
Write-Host "===== 校验结果 =====" -ForegroundColor Cyan

# 1) eboot @0x0
$eb = Hex $dump 0 8
$ebOk = $dump[0] -eq 0xE9
Write-Host ("[1] 0x000000 eboot 头      : {0}   {1}" -f $eb, $(if ($ebOk) { 'OK' } else { '失败' })) -ForegroundColor $(if ($ebOk) { 'Green' } else { 'Red' })
if (-not $ebOk) { $ok = $false }

# 2) app @0x1000
$ap = Hex $dump 0x1000 8
$apOk = $dump[0x1000] -eq 0xE9
Write-Host ("[2] 0x001000 应用镜像头    : {0}   {1}" -f $ap, $(if ($apOk) { 'OK' } else { '失败' })) -ForegroundColor $(if ($apOk) { 'Green' } else { 'Red' })
if (-not $apOk) { $ok = $false }

# 3) 与镜像逐字节比对
$match = $true
for ($i = 0; $i -lt $fw.Length; $i++) {
  if ($dump[$i] -ne $fw[$i]) { $match = $false; Write-Host ("    首个不一致偏移: 0x{0:X}" -f $i) -ForegroundColor Red; break }
}
Write-Host ("[3] 0x0..0x{0:X} 与镜像比对 : {1}" -f ($fw.Length - 1), $(if ($match) { '逐字节一致 OK' } else { '不一致 失败' })) -ForegroundColor $(if ($match) { 'Green' } else { 'Red' })
if (-not $match) { $ok = $false }

# 4) 配置扇区 0xFB000
$cfg = $dump[0xFB000..0xFB01F]
$blank = -not ($cfg | Where-Object { $_ -ne 0xFF })
Write-Host ("[4] 0x0FB000 配置扇区      : {0}" -f $(if ($blank) { '空白 → 首次上电进配网热点模式' } else { '已有配置 → 直接连已保存的 WiFi' })) -ForegroundColor Yellow

# 5) 全片指纹
Write-Host ("[5] 整片 SHA256            : {0}" -f (Sha256Bytes $dump))
Write-Host ("    镜像 SHA256            : {0}" -f (Sha256Bytes $fw))

Remove-Item $tmp -Force
Write-Host ""
if ($ok) { Write-Host "校验通过 OK" -ForegroundColor Green; exit 0 }
Write-Host "校验失败" -ForegroundColor Red; exit 2
