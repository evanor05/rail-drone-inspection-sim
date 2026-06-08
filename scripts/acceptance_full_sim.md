# 完整仿真验收清单

适用环境：Windows + WSL2 Ubuntu + Docker Desktop。

## 启动完整仿真

```powershell
cd E:\DroneRailInspection
.\scripts\build.ps1
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

如果 WSLg/RViz 图形环境确认可用，可以去掉 `-NoRviz`：

```powershell
.\scripts\start_full_sim.ps1 -CleanBuild
```

## 执行验收

另开一个 PowerShell：

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

## Dashboard

```text
http://127.0.0.1:8080
```

如果 `localhost` 可用，也可以打开：

```text
http://localhost:8080
```

## 预期结果

- Gazebo 加载 `high_speed_rail_corridor.sdf`。
- PX4 SITL 启动 `gz_x500_depth`。
- Micro XRCE-DDS Agent 运行，并和 PX4 client 通信。
- ROS 2 中存在 `/fmu/in/offboard_control_mode`。
- ROS 2 中存在 `/fmu/in/trajectory_setpoint`。
- ROS 2 中存在 `/fmu/out/vehicle_local_position`。
- ROS 2 中存在 `/dri/camera/front/image_raw`。
- ROS 2 中存在 `/dri/detections`。
- ROS 2 中存在 `/dri/alerts`。
- ROS 2 中存在 `/dri/mission/state`。
- 中文 Dashboard 展示任务阶段、相机检测叠加画面、检测结果和告警记录。
- `data/reports/inspection_report.json`、`.md`、`.html` 生成并包含告警证据路径。

## 停止仿真

```powershell
docker rm -f drone-rail-inspection
```
