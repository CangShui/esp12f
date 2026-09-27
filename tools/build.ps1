# =============================================================================
#  ES12F 固件编译
#  用法:  .\build.ps1            编译并输出到 ..\build\
#         .\build.ps1 -Clean     先清空 build\ 再编译
# -----------------------------------------------------------------------------
#  依赖：toolchain\ 下的 arduino-cli + esp8266 core 3.1.2（已随仓库提供）
#        若 toolchain 被删，首次运行会自动联网下载（约 480MB）
# =============================================================================
[CmdletBinding()]
param(
  [switch]$Clean,
  [switch]$Verbose_Warnings
)

$ErrorActionPreference = 'Stop'
$Root      = Split-Path $PSScriptRoot -Parent
$Sketch    = Join-Path $Root 'firmware\ES12F_Local'
$BuildDir  = Join-Path $Root 'build'
$Cli       = Join-Path $Root 'toolchain\tools\arduino-cli.exe'
$Fqbn      = 'esp8266:esp8266:generic:eesz=1M,CrystalFreq=26'

if (-not (Test-Path $Cli)) {
  throw "找不到 $Cli —— toolchain 缺失。请重新下载 arduino-cli 与 esp8266 core 到 toolchain\ 下。"
}

# arduino-cli 的目录全部指向仓库内的 toolchain\，不污染用户全局环境
$env:ARDUINO_DIRECTORIES_DATA      = Join-Path $Root 'toolchain\arduino'
$env:ARDUINO_DIRECTORIES_DOWNLOADS = Join-Path $Root 'toolchain\ardl'
$env:ARDUINO_DIRECTORIES_USER      = Join-Path $Root 'toolchain\user'

if ($Clean -and (Test-Path $BuildDir)) {
  Get-ChildItem $BuildDir -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Write-Host "===== 编译 ES12F 固件 =====" -ForegroundColor Cyan
Write-Host "sketch : $Sketch"
Write-Host "输出   : $BuildDir"
Write-Host "FQBN   : $Fqbn"
Write-Host ""

$warn = if ($Verbose_Warnings) { 'all' } else { 'default' }
# arduino-cli 会把内存占用等信息写到 stderr；在 $ErrorActionPreference='Stop' 下，
# 原生命令的任何 stderr 输出都会被当成异常抛出，所以这里临时放宽，改用 $LASTEXITCODE 判断。
$ErrorActionPreference = 'Continue'
& $Cli compile -b $Fqbn --warnings $warn --output-dir $BuildDir $Sketch 2>&1 |
  ForEach-Object { Write-Host $_ }
$code = $LASTEXITCODE
$ErrorActionPreference = 'Stop'

Write-Host ""
if ($code -ne 0) { Write-Host "编译失败 (exit $code)" -ForegroundColor Red; exit $code }
Write-Host "编译成功" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：python .\make_images.py    # 生成可刷写镜像到 ..\release\" -ForegroundColor Yellow
