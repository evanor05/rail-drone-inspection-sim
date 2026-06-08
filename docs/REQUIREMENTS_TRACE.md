# Requirements Trace

This trace maps the requested first-stage and reserved second-stage capabilities to concrete project artifacts and validation commands.

## First Stage

| Requirement | Implementation | Validation |
| --- | --- | --- |
| Complete project and Docker/WSL2 development environment | `compose.yaml`, `docker/Dockerfile`, `docker/entrypoint.sh`, `scripts/*.ps1` | `docker compose config --quiet`, `.\scripts\build.ps1` |
| High-speed railway scenario | `rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf` | `python scripts/static_check.py` |
| PX4-controlled quadrotor in Gazebo | `full_sim.launch.py`, PX4 `gz_x500_depth`, `MicroXRCEAgent` | `.\scripts\start_full_sim.ps1`, `.\scripts\acceptance_full_sim.ps1` |
| Simulated sensors | PX4 front camera/depth model, Gazebo static reference cameras/IMU, synthetic GPS/IMU/downward image fallback node | `ros2 topic list`, `/dri/camera/front/image_raw`, `/dri/camera/down/image_raw`, `/dri/imu`, `/dri/gps/fix` |
| ROS2 reads state/images/environment and publishes offboard commands | `mission_manager.py`, `synthetic_scene_publisher.py`, `ros_gz_bridge`, `/fmu/in/*` publishers, `/fmu/out/*` subscriptions | `/dri/drone/telemetry`, `/dri/offboard/setpoint`, `/fmu/in/trajectory_setpoint` |
| Automatic inspection workflow | `MissionManager` state machine: takeoff, enter corridor, inspect, reinspect, return, land | `/dri/mission/state`, `/dri/mission/events` |
| YOLO detection node | `yolo_detector.py`, `FAULT_CLASSES`, ultralytics model loading and fallback detection | `/dri/detections`, `/dri/alerts`, `/dri/perception/debug_image` |
| Requested fault classes | `fault_catalog.py`, synthetic scene and world targets | `README.md`, `python scripts/static_check.py`, report classes |
| Web dashboard | `rail_inspection_dashboard/web_dashboard.py`, static web UI | `http://localhost:8080`, `/api/status`, `/api/alerts`, `/api/reports` |
| RViz2 visualization | `rail_inspection_bringup/rviz/rail_inspection.rviz` | `.\scripts\start_full_sim.ps1` with RViz |
| Automatic report | `report_generator.py`, `data/reports/inspection_report.{json,md,html}` | `python scripts/check_acceptance_artifacts.py` |
| Acceptance commands | `scripts/acceptance_offline.ps1`, `scripts/acceptance_full_sim.ps1`, `scripts/acceptance_full_sim.md` | Run scripts in Docker environment |

## Second Stage Reserved

| Requirement | Implementation | Validation |
| --- | --- | --- |
| Gymnasium environment wrapper | `rail_inspection_rl/env.py::RailInspectionEnv` | `ros2 run rail_inspection_rl rl_env_smoke` |
| Policy replacement interface | `RulePolicyAdapter` and mission boundary through `/dri/offboard/setpoint` | Code inspection and future ROS adapter tests |
| Training tasks for approach, avoidance, planning, efficiency | Observation/action/reward skeleton and task config | Extend `RailInspectionTaskConfig` |
| Real-drone migration | ROS2 topic contracts, PX4 uXRCE-DDS bridge, camera-topic abstraction | Replace Gazebo/synthetic publishers with real drivers |

## Current Host Validation Status

Validated in the current restricted environment:

- Static project validation passed.
- Docker Compose file parses.
- Local report/evidence artifact smoke test passed.

Not yet validated because of host blockers:

- Docker image build.
- ROS2 workspace build inside container.
- PX4 SITL startup.
- Gazebo rendering.
- uXRCE-DDS PX4 bridge live topics.
- Dashboard live ROS topic updates.

See `docs/HOST_CHECK_2026-06-07.md` for the current host blockers observed on this machine.
