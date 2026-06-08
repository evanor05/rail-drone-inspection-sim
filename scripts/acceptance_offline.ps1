param(
    [int]$Seconds = 35,
    [int]$DashboardPort = 8080
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[DRI] Running offline acceptance for $Seconds seconds"
$cmd = @'
set -eo pipefail
cd /workspace
source /opt/px4_ros2_ws/install/setup.bash
rm -rf ros2_ws/build ros2_ws/install ros2_ws/log
colcon --log-base ros2_ws/log build --symlink-install --base-paths ros2_ws/src --build-base ros2_ws/build --install-base ros2_ws/install
source ros2_ws/install/setup.bash
export DRI_DASHBOARD_PORT=__DASHBOARD_PORT__
timeout __SECONDS__s ros2 launch rail_inspection_bringup offline_demo.launch.py dashboard_port:=__DASHBOARD_PORT__ || code=$?
if [ "${code:-0}" != "124" ] && [ "${code:-0}" != "0" ]; then exit "${code}"; fi
python3 scripts/check_acceptance_artifacts.py --report data/reports/inspection_report.json --min-alerts 1
'@
$cmd = $cmd.Replace("__SECONDS__", [string]$Seconds).Replace("__DASHBOARD_PORT__", [string]$DashboardPort)

docker compose run --rm --name drone-rail-inspection-acceptance --service-ports -e DRI_SKIP_WORKSPACE_SETUP=1 drone-rail bash -lc $cmd
