param(
    [int]$DashboardPort = 8080
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[DRI] Starting offline ROS2 demo on dashboard port $DashboardPort"
$env:DRI_DASHBOARD_PORT = "$DashboardPort"
docker compose run --rm --name drone-rail-inspection --service-ports -e DRI_SKIP_WORKSPACE_SETUP=1 -e DRI_DASHBOARD_PORT=$DashboardPort drone-rail bash -lc "cd /workspace && source /opt/px4_ros2_ws/install/setup.bash && colcon --log-base ros2_ws/log build --symlink-install --base-paths ros2_ws/src --build-base ros2_ws/build --install-base ros2_ws/install && source ros2_ws/install/setup.bash && ros2 launch rail_inspection_bringup offline_demo.launch.py dashboard_port:=$DashboardPort"
