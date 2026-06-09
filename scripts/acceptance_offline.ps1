param(
    [int]$Seconds = 35,
    [int]$DashboardPort = 8080,
    [string]$MissionProfile = "/workspace/data/missions/default_corridor_profile.json",
    [string]$Scenario = "/workspace/data/scenarios/default_synthetic_faults.json"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Convert-ToContainerWorkspacePath {
    param([string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return "/workspace/data/missions/default_corridor_profile.json"
    }

    $trimmed = $PathValue.Trim()
    if ($trimmed.StartsWith("/workspace/") -or $trimmed.StartsWith("/")) {
        return $trimmed
    }

    if ([System.IO.Path]::IsPathRooted($trimmed)) {
        $hostPath = $trimmed
    } else {
        $hostPath = Join-Path $Root $trimmed
    }

    if (-not (Test-Path -LiteralPath $hostPath)) {
        throw "Workspace path not found: $hostPath"
    }

    $resolved = (Resolve-Path -LiteralPath $hostPath).Path
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path.TrimEnd("\")
    if (-not $resolved.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must be under $Root or already use a /workspace path: $PathValue"
    }

    $relative = $resolved.Substring($resolvedRoot.Length).TrimStart("\")
    return "/workspace/" + ($relative -replace "\\", "/")
}

$MissionProfileInContainer = Convert-ToContainerWorkspacePath $MissionProfile
$ScenarioInContainer = Convert-ToContainerWorkspacePath $Scenario

Write-Host "[DRI] Running offline acceptance for $Seconds seconds"
Write-Host "[DRI] Mission profile: $MissionProfileInContainer"
Write-Host "[DRI] Synthetic scenario: $ScenarioInContainer"
$cmd = @'
set -eo pipefail
cd /workspace
source /opt/px4_ros2_ws/install/setup.bash
rm -rf ros2_ws/build ros2_ws/install ros2_ws/log
colcon --log-base ros2_ws/log build --symlink-install --base-paths ros2_ws/src --build-base ros2_ws/build --install-base ros2_ws/install
source ros2_ws/install/setup.bash
export DRI_DASHBOARD_PORT=__DASHBOARD_PORT__
export DRI_MISSION_PROFILE_PATH=__MISSION_PROFILE__
export DRI_SYNTHETIC_SCENARIO_PATH=__SCENARIO__
timeout __SECONDS__s ros2 launch rail_inspection_bringup offline_demo.launch.py dashboard_port:=__DASHBOARD_PORT__ mission_profile_path:=__MISSION_PROFILE__ scenario_path:=__SCENARIO__ || code=$?
if [ "${code:-0}" != "124" ] && [ "${code:-0}" != "0" ]; then exit "${code}"; fi
python3 scripts/check_acceptance_artifacts.py --report data/reports/inspection_report.json --min-alerts 1
'@
$cmd = $cmd.Replace("__SECONDS__", [string]$Seconds).Replace("__DASHBOARD_PORT__", [string]$DashboardPort)
$cmd = $cmd.Replace("__MISSION_PROFILE__", $MissionProfileInContainer).Replace("__SCENARIO__", $ScenarioInContainer)

docker compose run --rm --name drone-rail-inspection-acceptance --service-ports -e DRI_SKIP_WORKSPACE_SETUP=1 -e DRI_MISSION_PROFILE_PATH=$MissionProfileInContainer -e DRI_SYNTHETIC_SCENARIO_PATH=$ScenarioInContainer drone-rail bash -lc $cmd
