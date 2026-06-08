param(
    [int]$DashboardPort = 8080,
    [switch]$NoRviz,
    [switch]$CleanBuild
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$rviz = if ($NoRviz) { "false" } else { "true" }
$clean = if ($CleanBuild) { "rm -rf ros2_ws/build ros2_ws/install ros2_ws/log && " } else { "" }
Write-Host "[DRI] Starting full PX4/Gazebo sim dashboard=$DashboardPort rviz=$rviz"
$env:DRI_DASHBOARD_PORT = "$DashboardPort"
docker compose run --rm --name drone-rail-inspection --service-ports -e DRI_SKIP_WORKSPACE_SETUP=1 -e DRI_DASHBOARD_PORT=$DashboardPort drone-rail bash -lc "cd /workspace && source /opt/px4_ros2_ws/install/setup.bash && ${clean}colcon --log-base ros2_ws/log build --symlink-install --base-paths ros2_ws/src --build-base ros2_ws/build --install-base ros2_ws/install && source ros2_ws/install/setup.bash && ros2 launch rail_inspection_bringup full_sim.launch.py dashboard_port:=$DashboardPort rviz:=$rviz"
