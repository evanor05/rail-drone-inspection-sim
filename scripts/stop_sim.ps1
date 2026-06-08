$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[DRI] Stopping simulation container if it exists..."
docker rm -f drone-rail-inspection
Write-Host "[DRI] Current container state:"
docker ps -a --filter name=drone-rail-inspection --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"