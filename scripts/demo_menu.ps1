param(
    [int]$DashboardPort = 8080
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Show-Menu {
    Write-Host ""
    Write-Host "==== DroneRailInspection 演示菜单 ===="
    Write-Host "1. 查看状态"
    Write-Host "2. 启动离线工程演示"
    Write-Host "3. 启动完整 PX4/Gazebo 仿真（无 RViz）"
    Write-Host "4. 打开 Dashboard"
    Write-Host "5. 运行离线验收"
    Write-Host "6. 运行完整仿真验收"
    Write-Host "7. 停止仿真容器"
    Write-Host "8. 打开容器 shell"
    Write-Host "0. 退出"
}

while ($true) {
    Show-Menu
    $choice = Read-Host "请选择操作"
    switch ($choice) {
        "1" { & .\scripts\status.ps1 -DashboardPort $DashboardPort }
        "2" { & .\scripts\start_offline_demo.ps1 -DashboardPort $DashboardPort }
        "3" { & .\scripts\start_full_sim.ps1 -DashboardPort $DashboardPort -NoRviz -CleanBuild }
        "4" { & .\scripts\open_dashboard.ps1 -DashboardPort $DashboardPort }
        "5" { & .\scripts\acceptance_offline.ps1 -Seconds 35 }
        "6" { & .\scripts\acceptance_full_sim.ps1 -DashboardPort $DashboardPort -MinAlerts 1 }
        "7" { & .\scripts\stop_sim.ps1 }
        "8" { & .\scripts\shell.ps1 }
        "0" { break }
        default { Write-Host "未知选项: $choice" }
    }
}