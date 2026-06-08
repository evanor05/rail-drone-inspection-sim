param(
    [switch]$CudaTorch,
    [switch]$Ultralytics,
    [string]$Px4Version = "v1.16.2",
    [string]$GitMirrorPrefix = ""
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[DRI] Project root: $Root"
docker version | Out-Host

$env:PX4_VERSION = $Px4Version
$env:INSTALL_TORCH_CUDA = if ($CudaTorch) { "true" } else { "false" }
$env:INSTALL_ULTRALYTICS = if ($Ultralytics) { "true" } else { "false" }
$env:GIT_MIRROR_PREFIX = $GitMirrorPrefix

Write-Host "[DRI] Building Docker image PX4=$env:PX4_VERSION INSTALL_TORCH_CUDA=$env:INSTALL_TORCH_CUDA INSTALL_ULTRALYTICS=$env:INSTALL_ULTRALYTICS GIT_MIRROR_PREFIX=$env:GIT_MIRROR_PREFIX"
docker compose --progress=plain build
if ($LASTEXITCODE -ne 0) {
    throw "docker compose build failed with exit code $LASTEXITCODE"
}
