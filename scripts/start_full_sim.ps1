param(
    [int]$DashboardPort = 8080,
    [switch]$NoRviz,
    [switch]$CleanBuild,
    [string]$MissionProfile = "/workspace/data/missions/default_corridor_profile.json"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$rviz = if ($NoRviz) { "false" } else { "true" }
$clean = if ($CleanBuild) { "rm -rf ros2_ws/build ros2_ws/install ros2_ws/log && " } else { "" }

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
        throw "Mission profile not found: $hostPath"
    }

    $resolved = (Resolve-Path -LiteralPath $hostPath).Path
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path.TrimEnd("\")
    if (-not $resolved.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Mission profile must be under $Root or already use a /workspace path: $PathValue"
    }

    $relative = $resolved.Substring($resolvedRoot.Length).TrimStart("\")
    return "/workspace/" + ($relative -replace "\\", "/")
}

$MissionProfileInContainer = Convert-ToContainerWorkspacePath $MissionProfile

Write-Host "[DRI] Starting full PX4/Gazebo sim dashboard=$DashboardPort rviz=$rviz"
Write-Host "[DRI] Mission profile: $MissionProfileInContainer"
$env:DRI_DASHBOARD_PORT = "$DashboardPort"
docker compose run --rm --name drone-rail-inspection --service-ports -e DRI_SKIP_WORKSPACE_SETUP=1 -e DRI_DASHBOARD_PORT=$DashboardPort -e DRI_MISSION_PROFILE_PATH=$MissionProfileInContainer drone-rail bash -lc "cd /workspace && source /opt/px4_ros2_ws/install/setup.bash && ${clean}colcon --log-base ros2_ws/log build --symlink-install --base-paths ros2_ws/src --build-base ros2_ws/build --install-base ros2_ws/install && source ros2_ws/install/setup.bash && ros2 launch rail_inspection_bringup full_sim.launch.py dashboard_port:=$DashboardPort rviz:=$rviz mission_profile_path:=$MissionProfileInContainer"
