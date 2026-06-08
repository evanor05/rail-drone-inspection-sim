param(
    [int]$DashboardPort = 8080
)

$ErrorActionPreference = "Continue"
$url = "http://127.0.0.1:$DashboardPort"
Write-Host "[DRI] Opening Dashboard: $url"
Start-Process $url