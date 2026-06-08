param(
    [string]$Target = "E:\DroneRailInspection",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $PSScriptRoot

if (Test-Path $Target) {
    if (-not $Overwrite) {
        throw "Target already exists: $Target. Re-run with -Overwrite after backing up anything you need."
    }
    $resolved = Resolve-Path $Target
    if ($resolved.Path -ne "E:\DroneRailInspection") {
        throw "Refusing to overwrite unexpected target: $resolved"
    }
    Remove-Item -LiteralPath $Target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item -Path (Join-Path $Source "*") -Destination $Target -Recurse -Force
Write-Host "[DRI] Installed project to $Target"
Write-Host "[DRI] Next:"
Write-Host "  cd $Target"
Write-Host "  .\scripts\doctor.ps1"
Write-Host "  .\scripts\build.ps1"
Write-Host "  .\scripts\acceptance_offline.ps1 -Seconds 35"
