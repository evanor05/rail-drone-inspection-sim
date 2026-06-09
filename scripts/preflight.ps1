param(
    [int]$DashboardPort = 8080,
    [switch]$SkipDockerCompose
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($Name, [scriptblock]$Block) {
    Write-Host "== $Name =="
    & $Block
    Write-Host "[PASS] $Name"
    Write-Host ""
}

Step "Static project check" {
    python .\scripts\static_check.py
}

Step "Mission profile check" {
    python .\scripts\mission_profile_check.py
}

Step "Synthetic scenario check" {
    python .\scripts\scenario_check.py
}

if (-not $SkipDockerCompose) {
    Step "Docker Compose config" {
        docker compose config --quiet
    }
}

Step "PowerShell script parse" {
    $files = Get-ChildItem .\scripts -Filter *.ps1
    foreach ($file in $files) {
        $tokens = $null
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors) | Out-Null
        if ($errors -and $errors.Count -gt 0) {
            throw "PowerShell parse failed: $($file.FullName) $($errors | Out-String)"
        }
    }
}

Write-Host "== Optional Dashboard API check =="
try {
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:$DashboardPort/api/status" -TimeoutSec 3
    Write-Host "Dashboard API reachable. phase=$($status.mission.phase) alerts=$(@($status.alerts).Count)"
} catch {
    Write-Host "Dashboard API not reachable. This is OK when the simulation is not running. $($_.Exception.Message)"
}
Write-Host ""
Write-Host "[PASS] Preflight complete"
