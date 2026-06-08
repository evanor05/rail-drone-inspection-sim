#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash

if [ -f /workspace/ros2_ws/install/setup.bash ] && [ -z "${DRI_SKIP_WORKSPACE_SETUP:-}" ]; then
  source /workspace/ros2_ws/install/setup.bash
fi

export PX4_HOME="${PX4_HOME:-/opt/PX4-Autopilot}"
export GZ_SIM_RESOURCE_PATH="/workspace/ros2_ws/src/rail_inspection_gazebo/worlds:/workspace/ros2_ws/src/rail_inspection_gazebo/models:${GZ_SIM_RESOURCE_PATH:-}"
export DRI_REPORT_DIR="${DRI_REPORT_DIR:-/workspace/data/reports}"
export DRI_EVIDENCE_DIR="${DRI_EVIDENCE_DIR:-/workspace/data/evidence}"

exec "$@"
