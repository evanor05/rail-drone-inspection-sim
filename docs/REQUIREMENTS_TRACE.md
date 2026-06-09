# 需求追踪与验收矩阵

本文把第一阶段工程演示目标、第二阶段预留目标和真实无人机迁移方向映射到当前仓库中的具体实现、验证命令和剩余风险。它用于 GitHub 展示、交接说明和后续回归验收。

## 当前结论

当前项目已经不是空项目或安装脚本集合，而是具备可运行闭环的高铁无人机巡检仿真工程：

- 离线工程演示可验证 ROS 2 业务链路、合成相机、检测、告警、中文 Dashboard 和报告生成。
- 完整仿真链路已按 PX4 SITL + Gazebo Harmonic + ROS 2 Humble + uXRCE-DDS 设计，并提供启动和验收脚本。
- YOLO 节点支持真实权重路径，同时保留 deterministic fallback detector，保证没有真实铁路模型时也能跑通工程验收。
- 报告、Dashboard、消息接口和任务控制节点尽量使用 `/dri/*` 抽象，不把业务层强绑定到 Gazebo，便于后续迁移到真实 PX4 飞控和 companion computer。

## 第一阶段工程演示目标

| 序号 | 目标 | 当前实现 | 验收证据/命令 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | 完整项目结构和 Docker/WSL2 开发环境 | `compose.yaml`、`docker/Dockerfile`、`docker/entrypoint.sh`、`scripts/*.ps1`、ROS 2 workspace | `python scripts/static_check.py`、`docker compose config --quiet`、`.\scripts\build.ps1` | 已实现 |
| 2 | 高铁线路仿真场景 | `rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf`，包含双线轨道、无砟轨道板、扣件、接触网、护栏、隧道口、弯道、高架/路基和缺陷目标 | `python scripts/static_check.py` 的 world feature coverage | 已实现，工程几何级 |
| 3 | Gazebo 中启动 PX4 控制四旋翼 | `rail_inspection_bringup/launch/full_sim.launch.py` 启动 PX4 `gz_x500_depth`、Gazebo Harmonic 和 Micro XRCE-DDS Agent | `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild`、`.\scripts\acceptance_full_sim.ps1` | 已接入 |
| 4 | 仿真传感器 | 前视/下视相机 topic、IMU/GPS 合成 topic、PX4/Gazebo 图像桥接，必要时可接深度相机路径 | `/dri/camera/front/image_raw`、`/dri/camera/down/image_raw`、`/dri/imu`、`/dri/gps/fix` | 已实现演示链路 |
| 5 | ROS 2 读取状态/图像/环境并发布 offboard 指令 | `mission_manager.py` 订阅状态和告警，发布 `/dri/offboard/setpoint`，在有 `px4_msgs` 时发布 `/fmu/in/*` | `/dri/drone/telemetry`、`/dri/offboard/setpoint`、`/fmu/in/trajectory_setpoint` | 已实现 |
| 6 | 自动巡检流程 | 规则状态机覆盖起飞、进入线路走廊、沿轨巡检、异常复查、记录告警、继续巡检、返航降落；航线和复查参数已抽成 `data/missions/default_corridor_profile.json` | `/dri/mission/state`、Dashboard 任务阶段、告警日志、`python scripts/mission_profile_check.py` | 已实现并支持配置化 |
| 7 | YOLO 检测节点 | `rail_inspection_perception/yolo_detector.py` 支持 Ultralytics 权重和 fallback detector，发布检测、告警和 debug image | `/dri/detections`、`/dri/alerts`、`/dri/perception/debug_image` | 已实现 |
| 8 | 十类故障类别 | `fault_catalog.py`、合成场景和检测节点覆盖用户指定类别；真实精度依赖后续 `rail_defects.pt` | `README.md` 类别清单、`static_check.py`、报告 smoke | 已建模，真实训练待扩展 |
| 9 | Web Dashboard | `rail_inspection_dashboard/web_dashboard.py` 和中文静态页面展示状态、任务、检测、告警、报告入口 | `http://127.0.0.1:8080`、`/api/status`、`/api/alerts`、`/api/reports` | 已实现 |
| 10 | RViz2 可视化 | `rail_inspection_bringup/rviz/rail_inspection.rviz` 配置路径、marker、TF、debug image 和关键 topic | `.\scripts\start_full_sim.ps1` 不加 `-NoRviz` | 已配置 |
| 11 | 自动巡检报告 | `report_generator.py` + `report_templates.py` 输出 JSON、Markdown、HTML，包含时间、类别、置信度、位置和证据路径 | `python scripts/report_smoke.py`、`data/reports/inspection_report.*` | 已实现 |
| 12 | 可运行验收脚本/命令 | `acceptance_offline.ps1`、`acceptance_full_sim.ps1`、`preflight.ps1`、`static_check.py` | `.\scripts\preflight.ps1`、`.\scripts\acceptance_offline.ps1 -Seconds 35`、`.\scripts\acceptance_full_sim.ps1` | 已实现 |

## 第二阶段预留目标

| 目标 | 当前实现 | 下一步 |
| --- | --- | --- |
| Gymnasium 环境封装 | `rail_inspection_rl/env.py::RailInspectionEnv` 预留 observation/action/reward skeleton，并提供 `scripts/rl_smoke.py` 验证入口 | 接入真实 ROS/Gazebo adapter，支持批量 episode |
| 策略替换接口 | `RulePolicyAdapter`、`rl_policy_eval` 和 `/dri/offboard/setpoint` policy boundary | 抽象 mission manager，使规则策略、启发式策略和 RL policy 可切换 |
| 目标靠近、避障、路径规划、效率优化 | 当前状态机已具备异常复查流程，RL 包预留任务配置 | 增加障碍物传感器、覆盖率指标、能耗指标、定位误差指标 |
| 不要求第一阶段训练结果 | 当前仓库不包含训练产物，不把 RL 训练作为第一阶段验收条件 | 后续补训练脚本、评估脚本、实验报告和模型注册目录 |

## 真实无人机迁移方向

| 迁移点 | 当前设计 | 真实部署替换项 |
| --- | --- | --- |
| 飞控链路 | PX4 SITL + uXRCE-DDS + `/fmu/*` topic | PX4 实飞飞控 + companion computer + Micro XRCE-DDS Agent |
| 相机链路 | Gazebo/合成 `sensor_msgs/Image` | 真实前视/下视/云台相机 ROS 2 driver |
| 定位链路 | 仿真 pose、GPS/IMU 合成 topic、PX4 local position | RTK/GNSS、PX4 EKF、里程标/线路坐标转换 |
| 感知链路 | YOLO 节点消费标准 image topic | Jetson Orin/Xavier 上运行 TensorRT/ONNX/PyTorch YOLO |
| 告警和报告 | `/dri/alerts`、报告 JSON/Markdown/HTML | 接入资产系统、工单系统、真实经纬度和证据图片归档 |
| 安全策略 | 仿真状态机和返航降落流程 | 地理围栏、低电量返航、失联返航、人工接管、飞行审批和 HITL 回归 |

## 推荐验收顺序

1. 静态检查：

```powershell
cd E:\DroneRailInspection
python .\scripts\static_check.py
```

2. 任务剖面校验：

```powershell
python .\scripts\mission_profile_check.py
```

3. 报告模板 smoke：

```powershell
python .\scripts\report_smoke.py
```

4. RL 接口 smoke：

```powershell
python .\scripts\rl_smoke.py
```

宿主机没有 Gymnasium/Numpy 时该命令会返回 SKIP；在 Docker/ROS 环境内可用 `ros2 run rail_inspection_rl rl_policy_eval --episodes 3 --max-steps 360` 运行真实基线评估。

5. Docker/脚本预检：

```powershell
.\scripts\preflight.ps1
```

如果 Docker Desktop 暂时未启动，但只想检查非 Docker 内容：

```powershell
.\scripts\preflight.ps1 -SkipDockerCompose
```

6. 离线工程演示验收：

```powershell
.\scripts\start_offline_demo.ps1
.\scripts\acceptance_offline.ps1 -Seconds 35
```

7. 完整 PX4/Gazebo 验收：

```powershell
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

## 当前剩余风险

- Gazebo 世界是工程几何级场景，不是照片级数字孪生；适合流程验收和策略开发，后续应扩展真实纹理、天气、光照和参数化场景生成。
- fallback detector 用于稳定演示，不代表真实铁路缺陷检测精度；真实落地需要训练 `data/models/rail_defects.pt` 并建立 mAP、召回率、误报率评估。
- 默认完整验收为 headless/server-only，RViz 和 Gazebo GUI 依赖 WSLg/X11/OpenGL 环境。
- 完整仿真依赖 Docker Desktop、WSL2、GPU 驱动、PX4/Gazebo 依赖下载和端口映射，主机状态会影响运行。
- 真实无人机迁移需要额外安全机制，包括地理围栏、失联/低电量策略、人工接管、空域审批和 HITL/SITL 回归。
