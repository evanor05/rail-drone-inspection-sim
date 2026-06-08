# 演示脚本与仿真操作矩阵

本文用于 GitHub 展示、答辩演示或给别人复现时使用。目标是让观众清楚看到：系统不是静态网页，而是包含 ROS 2、PX4/Gazebo、检测、告警、报告和后续 RL 接口的完整工程演示链路。

## 推荐讲解顺序

1. 说明场景：高铁线路巡检，关注人员侵限、异物、扣件、钢轨、轨道板、护栏、接触网等风险。
2. 说明架构：Windows + WSL2 + Docker，容器内运行 ROS 2 Humble、PX4 SITL、Gazebo Harmonic、uXRCE-DDS、感知与 Dashboard。
3. 先跑离线演示，快速展示中文 Dashboard、检测、告警和报告。
4. 再说明完整仿真如何启动，强调 PX4/Gazebo/ROS 2 topic 全链路已经验收。
5. 展示报告文件和证据图路径。
6. 说明下一步：真实 YOLO 权重、场景高保真、RL policy、真实无人机迁移。

## 仿真模式矩阵

| 模式 | 适用场景 | 启动命令 | 看什么 | 验收命令 |
| --- | --- | --- | --- | --- |
| 本地静态检查 | 上传前、修改后快速检查 | `python .\scripts\static_check.py` | 文件、Python、XML/SDF、场景覆盖 | 同启动命令 |
| 离线工程演示 | 最快展示 Dashboard 和业务闭环 | `.\scripts\start_offline_demo.ps1` | 中文 Dashboard、检测框、告警、报告 | `.\scripts\acceptance_offline.ps1 -Seconds 35` |
| 完整 PX4/Gazebo headless | 验证 PX4/Gazebo/ROS2 集成 | `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild` | `/fmu/*`、`/dri/*`、Dashboard、报告 | `.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1` |
| 完整 PX4/Gazebo + RViz | 图形环境可用时展示轨迹/marker | `.\scripts\start_full_sim.ps1 -CleanBuild` | RViz 路径、航点、marker、debug image | 同 full acceptance |
| YOLO 权重模式 | 接入真实模型后验证推理 | `.\scripts\build.ps1 -Ultralytics` 后启动 demo | 真实模型检测结果和报告 | offline/full acceptance + 模型评估脚本 |

## 离线演示具体步骤

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_offline_demo.ps1
```

打开：

```text
http://127.0.0.1:8080
```

讲解点：

- `任务阶段`：从进入线路走廊到异常复查。
- `当前位置`：无人机仿真坐标。
- `检测 / 告警`：当前 Dashboard 缓存中的检测和告警数量。
- `最新检测结果`：检测类别、置信度、轨道侧别、估计位置。
- `告警记录`：严重级别、任务阶段、证据路径。
- `巡检报告`：打开 HTML 报告。

## 完整 PX4/Gazebo 具体步骤

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

等待日志出现：

```text
Uvicorn running on http://0.0.0.0:8080
```

另开 PowerShell：

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

讲解点：

- PX4 SITL 运行 `gz_x500_depth`。
- Micro XRCE-DDS Agent 连接 PX4 client。
- ROS 2 可见 `/fmu/in/trajectory_setpoint` 和 `/fmu/out/vehicle_local_position`。
- 业务侧 `/dri/mission/state`、`/dri/detections`、`/dri/alerts` 正常。
- Dashboard 与报告链路仍然工作。

## RViz2 展示步骤

如果 WSLg 图形环境可用：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -CleanBuild
```

RViz 中重点看：

- 任务航点。
- 巡检路径。
- 告警 marker。
- debug image。
- TF/map 参考系。

如果 RViz 或 Gazebo 图形窗口不稳定，回到 headless：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz
```

## 报告展示步骤

报告目录：

```text
E:\DroneRailInspection\data\reports
```

重点文件：

```text
inspection_report.html
inspection_report.json
inspection_report.md
```

证据目录：

```text
E:\DroneRailInspection\data\evidence
```

讲解点：

- 报告包含时间、类别、置信度、位置、任务阶段和证据路径。
- 运行产物默认不提交 GitHub，避免仓库膨胀。
- 真实部署时可把证据路径替换为对象存储、数据库或线路资产系统。

## 停止与清理

停止当前仿真：

```powershell
docker rm -f drone-rail-inspection
```

检查是否还在运行：

```powershell
docker ps --filter name=drone-rail-inspection
```

如需清理 ROS workspace 构建产物，优先使用脚本参数：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

## GitHub 展示建议

上传 GitHub 后建议补充：

1. 中文 Dashboard 截图。
2. 一张架构图。
3. 一段 30-60 秒演示 GIF。
4. Full acceptance 通过截图或日志摘要。
5. 后续路线图：真实 YOLO、场景增强、RL、真实无人机迁移。
## 交互式菜单演示

如果演示对象不熟悉命令，可以直接运行：

```powershell
cd E:\DroneRailInspection
.\scripts\demo_menu.ps1
```

推荐演示选择顺序：

1. `1. 查看状态`
2. `2. 启动离线工程演示`
3. `4. 打开 Dashboard`
4. `5. 运行离线验收`
5. `7. 停止仿真容器`

完整仿真展示时选择：

1. `3. 启动完整 PX4/Gazebo 仿真（无 RViz）`
2. 另开一个菜单或 PowerShell 运行 `6. 运行完整仿真验收`
3. `7. 停止仿真容器`