# =============================================================================
#  ES12F 本地化固件 —— 刷写脚本 (Windows PowerShell)
# -----------------------------------------------------------------------------
#  ⚠ 关键：ESP8266 的 .ino.bin 是 [eboot@0x0]+[app@0x1000] 的合并镜像，
#     必须整体写到 flash 的 0x0。写到 0x1000 会导致入口非法指令异常死循环
#     （Fatal exception (0): epc1=0x4010f480）。
#
#  用法：
#    .\flash.ps1 -Mode Backup  -Port COM3     # 备份整片（1MB）
#    .\flash.ps1 -Mode Flash   -Port COM3     # 刷写 0x0，保留芯片上的 WiFi 配置
#    .\flash.ps1 -Mode Full    -Port COM3     # 写完整 1MB 出厂镜像（配置清空）
#    .\flash.ps1 -Mode Restore -Port COM3 -File ..\es12f_firmware_backup_1MB.bin
#    .\flash.ps1 -Mode Verify  -Port COM3     # 读回 0x0 比对
#
#  进下载模式（每次连接前都要重来）：
#    · GPIO0 接到 GND 并保持
#    · 保持 GPIO0 接地的状态下给模块断电 -> 再上电
#    · 下载模式下 ESP8266 不打印启动日志，属正常
#    · 板上的按键不是 GPIO0，按住按键上电无效
# =============================================================================
[CmdletBinding()]
param(
  [ValidateSet('Backup','Flash','Full','Restore','Verify')]
  [string]$Mode = 'Flash',
  [string]$Port = 'COM3',
  [int]$Baud = 460800,
  [string]$File,
  [string]$OutDir
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) { $OutDir = Join-Path $Root 'release' }

function Esptool([string[]]$esptoolArgs) {
  Write-Host ">> esptool --port $Port --baud $Baud --before no-reset $($esptoolArgs -join ' ')" -ForegroundColor DarkGray
  & python -m esptool --port $Port --baud $Baud --before no-reset --after no-reset @esptoolArgs
  if ($LASTEXITCODE -ne 0) { throw "esptool 失败 (exit $LASTEXITCODE)" }
}

function Sha256([string]$path) { (Get-FileHash -Algorithm SHA256 -Path $path).Hash }

$flashBin = Join-Path $OutDir 'ES12F_Local_firmware.bin'
$fullBin  = Join-Path $OutDir 'ES12F_Local_full_1MB.bin'
if (-not (Test-Path $flashBin)) { throw "缺少 $flashBin" }

Write-Host "===== ES12F 本地化固件刷写 =====" -ForegroundColor Cyan
Write-Host "端口: $Port   波特率: $Baud   模式: $Mode"
Write-Host ""

switch ($Mode) {
  'Backup' {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $out = Join-Path $OutDir "current_flash_backup_$stamp.bin"
    Write-Host "读取整片 1MB -> $out" -ForegroundColor Yellow
    Esptool @('read-flash','0x0','0x100000',$out)
    Write-Host "SHA256: $(Sha256 $out)" -ForegroundColor Green
  }

  'Flash' {
    Write-Host "写入 0x0：eboot + 应用（配置扇区 0xFB000 不动，原有 WiFi 保留）" -ForegroundColor Yellow
    Write-Host "  $flashBin"
    Write-Host "  SHA256 $(Sha256 $flashBin)"
    Esptool @('write-flash','0x0',$flashBin)
  }

  'Full' {
    if (-not (Test-Path $fullBin)) { throw "缺少 $fullBin" }
    Write-Host "写入 0x0：完整 1MB 出厂镜像（配置清空，首次上电进配网模式）" -ForegroundColor Yellow
    Write-Host "  $fullBin"
    Write-Host "  SHA256 $(Sha256 $fullBin)"
    Esptool @('write-flash','0x0',$fullBin)
  }

  'Restore' {
    if (-not $File) { throw '请用 -File 指定要刷回的 .bin' }
    if (-not (Test-Path $File)) { throw "找不到文件: $File" }
    Write-Host "刷回 $File" -ForegroundColor Yellow
    Write-Host "  SHA256 $(Sha256 $File)"
    Esptool @('write-flash','0x0',$File)
  }

  'Verify' {
    $size = (Get-Item $flashBin).Length
    $tmp = Join-Path $env:TEMP ("es12f_verify_{0}.bin" -f (Get-Random))
    Write-Host "读回 0x0 处 $size 字节并与镜像比对" -ForegroundColor Yellow
    Esptool @('read-flash','0x0',('0x{0:X}' -f $size),$tmp)
    $a = Sha256 $flashBin; $b = Sha256 $tmp
    Write-Host "镜像: $a"
    Write-Host "芯片: $b"
    if ($a -eq $b) { Write-Host "校验通过 OK" -ForegroundColor Green }
    else { Write-Host "校验失败" -ForegroundColor Red; Remove-Item $tmp -Force; exit 2 }
    Remove-Item $tmp -Force
  }
}

Write-Host ""
Write-Host "完成。断开 GPIO0 与 GND 后断电上电，新固件才会运行。" -ForegroundColor Cyan
