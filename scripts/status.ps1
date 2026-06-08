param(
    [int]$DashboardPort = 8080
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-DockerAvailable {
    docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

Write-Host "== DroneRailInspection 状态检查 =="
Write-Host "项目路径: $Root"
Write-Host "Dashboard: http://127.0.0.1:$DashboardPort"
Write-Host ""

$dockerAvailable = Test-DockerAvailable
Write-Host "== Docker 容器 =="
if ($dockerAvailable) {
    docker ps -a --filter name=drone-rail-inspection --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
} else {
    Write-Host "Docker Desktop 当前不可用或未启动。需要运行仿真时请先启动 Docker Desktop。"
}
Write-Host ""

Write-Host "== Dashboard API =="
try {
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:$DashboardPort/api/status" -TimeoutSec 3
    $mission = $status.mission
    $telemetry = $status.telemetry
    [PSCustomObject]@{
        UptimeSeconds = $status.uptime_seconds
        Phase = $mission.phase
        Progress = $mission.progress
        Target = $mission.active_target
        Alerts = @($status.alerts).Count
        Detections = @($status.detections).Count
        Position = if ($telemetry) { "x=$($telemetry.position.x), y=$($telemetry.position.y), z=$($telemetry.position.z)" } else { "--" }
        Battery = if ($telemetry) { "$($telemetry.battery_percentage)%" } else { "--" }
    } | Format-List
} catch {
    Write-Host "Dashboard API 暂不可访问: $($_.Exception.Message)"
}

Write-Host "== 报告文件 =="
Get-ChildItem .\data\reports -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table

Write-Host "== 证据文件数量 =="
try {
    $count = (Get-ChildItem .\data\evidence -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host $count
} catch {
    Write-Host "0"
}