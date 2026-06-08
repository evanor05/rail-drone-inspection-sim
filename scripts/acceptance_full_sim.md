# Full Simulation Acceptance Checklist

Run inside a working WSL2 Ubuntu + Docker Desktop environment:

```powershell
cd E:\DroneRailInspection
.\scripts\build.ps1
.\scripts\start_full_sim.ps1
```

In another terminal:

```powershell
.\scripts\acceptance_full_sim.ps1
```

Dashboard:

```text
http://localhost:8080
```

Expected:

- Gazebo opens `high_speed_rail_corridor.sdf`.
- PX4 SITL starts `gz_x500_depth` and uXRCE-DDS agent shows PX4 client connected.
- `/fmu/in/offboard_control_mode`, `/fmu/in/trajectory_setpoint`, `/dri/camera/front/image_raw`, `/dri/detections`, `/dri/alerts`, `/dri/mission/state` are present.
- Dashboard shows phase, camera overlay, detections, alerts.
- `data/reports/inspection_report.json`, `.md`, `.html` exist with alert evidence paths.
