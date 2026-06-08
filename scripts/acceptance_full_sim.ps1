param(
    [int]$DashboardPort = 8080,
    [int]$MinAlerts = 1
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[DRI] Checking full simulation acceptance through running container"

$cmd = @'
set -eo pipefail
DASHBOARD_PORT="$1"
MIN_ALERTS="$2"

cd /workspace
source /opt/ros/humble/setup.bash
source /opt/px4_ros2_ws/install/setup.bash
source ros2_ws/install/setup.bash

echo "[DRI] ROS topics:"
ros2 topic list | sort | tee /tmp/dri_topics.txt

for topic in \
  /dri/mission/state \
  /dri/drone/telemetry \
  /dri/detections \
  /dri/alerts \
  /dri/perception/debug_image \
  /fmu/in/trajectory_setpoint \
  /fmu/in/offboard_control_mode \
  /fmu/out/vehicle_local_position; do
  grep -q "^${topic}$" /tmp/dri_topics.txt
  echo "[PASS] topic ${topic}"
done

ros2 topic info -v /dri/camera/front/image_raw | tee /tmp/dri_front_image_info.txt
ros2 topic info -v /dri/perception/debug_image | tee /tmp/dri_debug_image_info.txt
grep -q 'Publisher count: [1-9]' /tmp/dri_front_image_info.txt
grep -q 'Publisher count: [1-9]' /tmp/dri_debug_image_info.txt
echo "[PASS] image/debug publishers are active"

python3 - "$DASHBOARD_PORT" "$MIN_ALERTS" <<'PY'
import json
import urllib.request
import sys
import time

port = int(sys.argv[1])
min_alerts = int(sys.argv[2])
url = f"http://127.0.0.1:{port}/api/status"
last = None
for _ in range(30):
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    last = payload
    if payload.get("mission") and len(payload.get("alerts", [])) >= min_alerts:
        print(
            json.dumps(
                {
                    "mission_phase": payload["mission"].get("phase"),
                    "alerts": len(payload.get("alerts", [])),
                    "detections": len(payload.get("detections", [])),
                },
                ensure_ascii=False,
            )
        )
        print("[PASS] Dashboard API reachable with live alerts")
        break
    time.sleep(1)
else:
    raise SystemExit(f"dashboard did not reach {min_alerts} alerts; last={last!r}")
PY

for attempt in $(seq 1 30); do
  if python3 scripts/check_acceptance_artifacts.py --report data/reports/inspection_report.json --min-alerts "$MIN_ALERTS"; then
    break
  fi
  if [ "$attempt" = "30" ]; then
    exit 1
  fi
  sleep 1
done
echo "[PASS] Full simulation acceptance checks completed"
'@

$cmd | docker exec -i drone-rail-inspection bash -s -- $DashboardPort $MinAlerts
if ($LASTEXITCODE -ne 0) {
    throw "full simulation acceptance failed with exit code $LASTEXITCODE"
}
