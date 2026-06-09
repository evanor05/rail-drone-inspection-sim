# DroneRailInspection 高铁无人机巡检仿真工程

本项目是面向高铁线路巡检的无人机仿真工程演示系统，运行目标环境为 Windows + WSL2 Ubuntu + Docker。第一阶段重点是可运行、可验收的工程链路，而不是玩具级最小 demo：项目包含高铁线路走廊 Gazebo 场景、PX4/Gazebo 启动链路、ROS 2 任务与感知节点、YOLO 兼容检测、Web Dashboard、RViz2 配置、告警持久化和巡检报告生成。

## 快速入口

- 详细中文使用手册：[docs/USAGE_CN.md](docs/USAGE_CN.md)
- 演示脚本与仿真操作矩阵：[docs/DEMO_SCRIPT_CN.md](docs/DEMO_SCRIPT_CN.md)
- 架构说明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 需求追踪：[docs/REQUIREMENTS_TRACE.md](docs/REQUIREMENTS_TRACE.md)
- 贡献与开发说明：[CONTRIBUTING.md](CONTRIBUTING.md)
- 完整仿真验收清单：[scripts/acceptance_full_sim.md](scripts/acceptance_full_sim.md)

最快演示：

```powershell
cd E:\DroneRailInspection
.\scripts\start_offline_demo.ps1
```

打开中文 Dashboard：

```text
http://127.0.0.1:8080
```


常用操作脚本：

```powershell
# 提交前/演示前预检
.\\scripts\\preflight.ps1

# 生成本地综合验证日志
.\scripts\verify_local.ps1

# 查看容器、Dashboard、报告和证据状态
.\scripts\status.ps1

# 打开中文 Dashboard
.\scripts\open_dashboard.ps1

# 停止当前仿真容器
.\scripts\stop_sim.ps1

# 使用交互式演示菜单
.\scripts\demo_menu.ps1

# 导出演示/验收证据包
.\scripts\export_evidence.ps1
```
完整 PX4/Gazebo 验收：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

## 技术版本选择

默认技术栈：

- Docker 内部使用 Ubuntu 22.04 / Jammy，基础镜像为 `ros:humble-ros-base-jammy`，桌面、仿真和构建依赖在 Dockerfile 中显式安装。
- ROS 2 Humble：Ubuntu 22.04 的稳定 LTS 版本，也适合后续迁移到 Jetson companion computer。
- PX4 Autopilot `v1.16.2`：PX4 v1.16 官方文档将 Gazebo Harmonic 作为匹配的 LTS Gazebo 线路。
- Gazebo Harmonic：LTS 支持到 2028 年，和 PX4 v1.16 匹配。
- PX4 ROS 2 bridge：使用 uXRCE-DDS agent/client 链路，将 PX4 uORB 消息暴露为 ROS 2 topic。

主要参考：

- PX4 v1.16 Gazebo simulation: https://docs.px4.io/v1.16/en/sim_gazebo_gz/index.html
- PX4 v1.16 release notes: https://docs.px4.io/main/en/releases/1.16
- PX4 uXRCE-DDS bridge: https://docs.px4.io/main/en/middleware/uxrce_dds
- Gazebo releases: https://gazebosim.org/docs/latest/releases/

## 项目目录

```text
E:\DroneRailInspection
  compose.yaml
  docker/
  scripts/
  data/
    models/        # 放置 rail_defects.pt 或 yolov8n.pt
    evidence/      # 检测截图和图像证据
    reports/       # JSON / Markdown / HTML 巡检报告
  ros2_ws/src/
    ddrone_msgs                 # Alert、Detection、Telemetry、MissionState 消息
    rail_inspection_gazebo      # 高铁线路 Gazebo 世界
    rail_inspection_control     # 巡检任务管理和 offboard setpoint
    rail_inspection_perception  # 合成相机 + YOLO/兜底检测器
    rail_inspection_report      # 巡检报告生成
    rail_inspection_dashboard   # FastAPI Web Dashboard
    rail_inspection_rl          # Gymnasium 强化学习扩展骨架
```

## 主机环境检查

在 PowerShell 中运行：

```powershell
cd E:\DroneRailInspection
.\scripts\doctor.ps1
```

需要满足：

- Docker Desktop 已启动，并启用 WSL2 backend。
- 至少安装一个 WSL2 Ubuntu 发行版。
- NVIDIA 驱动可通过 `nvidia-smi` 识别。
- 如果需要 GPU 容器，Docker Desktop 需要启用 GPU 集成并支持 NVIDIA container runtime。

如果 Docker Desktop 已安装但未启动：

```powershell
.\scripts\start_docker_desktop.ps1
```

如果 WSL 没有 Ubuntu 发行版，在管理员 PowerShell 中安装：

```powershell
wsl --install -d Ubuntu-22.04
```

安装后按提示重启 Windows，初始化 Ubuntu，并在 Docker Desktop 中启用 WSL integration。

## 安装到目标路径

项目目标路径为：

```powershell
E:\DroneRailInspection
```

如果当前仓库还在临时目录，可以复制到目标路径：

```powershell
.\scripts\install_to_target.ps1
```

如果目标路径已存在，并且确认要覆盖：

```powershell
.\scripts\install_to_target.ps1 -Overwrite
```

## 构建镜像

默认构建：

```powershell
cd E:\DroneRailInspection
.\scripts\build.ps1
```

启用 CUDA PyTorch wheel 路径：

```powershell
.\scripts\build.ps1 -CudaTorch
```

`-CudaTorch` 需要访问 `download.pytorch.org`。默认镜像仍支持 GPU passthrough，容器内有 CUDA 能力的库可以使用 GPU。

可选安装 Ultralytics/PyTorch：

```powershell
.\scripts\build.ps1 -Ultralytics
```

默认构建刻意不把 `ultralytics` 放进基础镜像，因为 PyTorch wheel 很大，在受限网络下容易失败。检测节点仍会使用确定性的高铁场景兜底检测器完成验收；如果要运行真实 YOLO 推理，请放入训练好的模型并使用 `-Ultralytics` 重新构建。

如果 PX4 或 eProsima 依赖下载时 GitHub 访问不稳定，可以传入当前网络可用的 GitHub 镜像或代理前缀：

```powershell
.\scripts\build.ps1 -GitMirrorPrefix "https://your-github-mirror/"
```

ROS 2 Humble 镜像固定使用 ROS 兼容的 NumPy 1.x ABI，避免 `cv_bridge` 和 ROS Python 消息扩展出现 NumPy ABI 问题。

## 已验证状态

本工作区在 2026-06-08 已完成验证：

- Docker 镜像 `drone-rail-inspection:humble-px4` 构建成功，最终镜像 ID 为 `291c7e1ca409`，大小约 `7.96GB`。
- Docker 容器内 GPU 可见，验证设备为 `NVIDIA GeForce RTX 4050 Laptop GPU`。
- `python .\scripts\static_check.py` 通过。
- `docker compose config --quiet` 通过。
- `.\scripts\acceptance_offline.ps1 -Seconds 45` 通过，并生成 JSON / Markdown / HTML 报告和图像证据。
- 完整 PX4/Gazebo 运行命令 `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild` 可启动 headless Gazebo、PX4 SITL `gz_x500_depth`、Micro XRCE-DDS Agent、ROS bridge、任务管理、检测、Dashboard 和报告节点。
- `.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1` 通过。验收观测到 `/fmu/in/*`、`/fmu/out/vehicle_local_position`、`/dri/*` topic，图像和 debug image publisher 正常，Dashboard 有实时告警，报告链路可用。
- 最新完整验收报告位于 `data/reports/inspection_report.json`、`data/reports/inspection_report.md`、`data/reports/inspection_report.html`，报告中包含告警、置信度、位置和证据图路径。

## 当前项目结论

当前项目不是“准备开始安装 WSL”的状态，而是已经完成第一阶段工程演示闭环，并在本机通过过完整验收。

已经可运行的能力：

- 一键构建 Docker 仿真环境。
- 启动离线工程演示，快速查看任务、检测、告警、Dashboard 和报告。
- 启动完整 PX4 + Gazebo + ROS 2 仿真链路。
- 在 Gazebo 高铁线路场景中运行 PX4 SITL 四旋翼。
- 通过 ROS 2 topic 传递任务状态、无人机状态、图像、检测、告警、报告信息。
- 自动执行巡检任务流程：进入线路走廊、沿轨巡检、发现异常、减速/复查、记录告警、继续巡检。
- 自动生成巡检报告和证据图片。
- 为后续真实 YOLO 模型、强化学习训练和真实无人机迁移保留接口。

当前最适合的使用方式：

- 日常演示和调试：先运行离线工程演示，速度最快、最稳定。
- 验证 PX4/Gazebo/ROS2 集成：运行完整仿真并执行 full acceptance。
- 后续算法开发：在当前工程框架上替换真实 YOLO 权重、扩展数据集、增强场景和巡检策略。

## 功能完成度

| 模块 | 当前程度 | 说明 |
| --- | --- | --- |
| Windows + WSL2 + Docker 环境 | 已完成并验证 | 已构建 `drone-rail-inspection:humble-px4` 镜像，GPU 在容器内可见 |
| ROS 2 工作区 | 已完成 | 包含消息、控制、感知、Dashboard、报告、Gazebo、RL 预留包 |
| PX4 SITL | 已接入并验收 | 使用 PX4 `v1.16.2`，通过 uXRCE-DDS 暴露 `/fmu/*` topic |
| Gazebo 仿真 | 已接入并验收 | 使用 Gazebo Harmonic，默认 headless/server-only 适配 WSL2 |
| 高铁线路场景 | 工程演示级完成 | 包含双线轨道、无砟轨道板、扣件、接触网、护栏、隧道口、弯道、高架/路基等元素 |
| 无人机传感器链路 | 工程演示级完成 | 接入前视/合成巡检相机、IMU、PX4 状态；真实载荷可后续替换 |
| 自动巡检任务 | 第一阶段完成 | 已实现规则状态机和 offboard setpoint 发布 |
| YOLO/检测节点 | 可运行，默认兜底检测 | 支持真实模型路径；默认用 synthetic fallback 保证验收稳定 |
| 告警和报告 | 已完成并验收 | JSON / Markdown / HTML 报告，包含类别、置信度、位置、证据路径 |
| Web Dashboard | 已完成并验收 | 展示任务阶段、无人机状态、检测结果、告警和 debug image |
| RViz2 可视化 | 已配置 | 用于路径、marker、TF、关键 topic 和 debug image 可视化 |
| Gymnasium/RL | 已预留骨架 | 尚未进入训练结果阶段，接口为后续研究扩展准备 |
| 真实无人机迁移 | 架构已考虑 | 感知、报告、Dashboard 不强绑定 Gazebo，可替换真实相机和 PX4 链路 |

## 最近一次验收记录

最近一次完整验收命令：

```powershell
cd E:\DroneRailInspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

验收结果摘要：

- `acceptance_full_sim.ps1` 返回 PASS。
- `/dri/mission/state`、`/dri/drone/telemetry`、`/dri/detections`、`/dri/alerts`、`/dri/perception/debug_image` 存在。
- `/fmu/in/trajectory_setpoint`、`/fmu/in/offboard_control_mode`、`/fmu/out/vehicle_local_position` 存在。
- `/dri/camera/front/image_raw` 有 synthetic camera 和 Gazebo bridge publisher。
- `/dri/perception/debug_image` 有 detector publisher。
- Dashboard API 返回实时任务状态、检测和告警。
- 报告链路生成 `inspection_report.json`、`inspection_report.md`、`inspection_report.html`。
- 最近报告中记录了 `person_on_track` 告警，并包含置信度、无人机位置、任务阶段和图像证据路径。

## 离线工程演示

离线模式不等待 PX4/Gazebo，主要验证任务状态机、相机、检测、告警、Dashboard 和报告生成链路。它发布和完整系统一致的 `/dri/*` topic。

```powershell
cd E:\DroneRailInspection
.\scripts\start_offline_demo.ps1
```

浏览器打开：

```text
http://localhost:8080
```

如果浏览器打不开，可以先验证 API：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8080/api/status -UseBasicParsing
```

正常情况下 `docker ps` 应显示类似端口映射：

```text
0.0.0.0:8080->8080/tcp
```

预期 topic：

```bash
ros2 topic list | grep /dri
ros2 topic echo --once /dri/mission/state
ros2 topic echo --once /dri/drone/telemetry
ros2 topic echo --once /dri/detections
ros2 topic echo --once /dri/alerts
```

报告输出：

```text
data/reports/inspection_report.json
data/reports/inspection_report.md
data/reports/inspection_report.html
data/evidence/*.jpg
```

演示或验收结束后，可以导出一份可交付的证据包：

```powershell
.\scripts\export_evidence.ps1 -DashboardPort 8080
```

默认输出到：

```text
data/exports/inspection-evidence-<timestamp>
```

证据包包含报告副本、证据文件索引、最近的证据文件、Dashboard API 快照、Git 状态、Docker 状态和主机摘要。`data/exports` 属于运行产物，默认不会提交到 Git。

## 离线验收命令

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_offline.ps1 -Seconds 35
```

该脚本会在容器内构建 ROS workspace，启动离线链路，等待检测和告警，然后检查生成的报告和证据文件。

如果 Docker 暂时不可用，可以用本地 smoke test 验证报告和证据链路：

```powershell
.\scripts\verify_local.ps1
python .\scripts\local_smoke.py
python .\scripts\check_acceptance_artifacts.py --report .\data\reports\inspection_report.json --min-alerts 1
```

这不能替代 ROS/PX4/Gazebo 验收，只用于验证业务报告格式和报告链路。

`verify_local.ps1` 会生成：

```text
data/exports/local-verify-<timestamp>
```

其中包含静态检查、中文报告 smoke、PowerShell 脚本解析和证据包导出 smoke 的日志。需要同时检查 Docker Compose 文件时可运行：

```powershell
.\scripts\verify_local.ps1 -WithDockerCompose
```

## 完整 PX4 + Gazebo 仿真

启动完整仿真：

```powershell
cd E:\DroneRailInspection
.\scripts\start_full_sim.ps1
```

不启动 RViz：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz
```

启动前清理并重建 ROS workspace：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

完整仿真会启动：

- Gazebo Harmonic 世界 `high_speed_rail_corridor.sdf`。默认使用 server-only/headless Gazebo，适合没有 X/WSLg 显示转发的 WSL2 环境。
- PX4 SITL `gz_x500_depth`，PX4 控制的四旋翼具备前视相机/深度载荷路径。
- 默认启用确定性的合成巡检相机，保证验收结果可重复，同时 PX4/Gazebo 仍然运行。Gazebo/PX4 相机 bridge 也存在；后续可用自定义 PX4 模型替换为真实前视/下视载荷。
- UDP `8888` 端口上的 Micro XRCE-DDS Agent。
- ROS-Gazebo 图像/IMU bridge。
- 巡检任务管理、检测、报告生成和 Dashboard 节点。
- RViz2，可视化任务路径、marker、TF 和 debug image。

完整验收清单：

```text
scripts/acceptance_full_sim.md
```

在 `start_full_sim.ps1` 运行期间执行验收：

```powershell
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

验收通过后如需停止容器：

```powershell
docker rm -f drone-rail-inspection
```

## 高铁线路场景覆盖

Gazebo 世界包含：

- 双线高铁线路。
- 无砟轨道板和轨道板接缝。
- 钢轨、扣件排、检修通道。
- 接触网杆和接触网线。
- 线路护栏和护栏侵限/损坏目标。
- 沿线设备线索。
- 路基、高架桥面、弯道预览和隧道口。
- 合成故障目标：
  - `person_on_track`
  - `foreign_object`
  - `rock_or_debris`
  - `fallen_branch`
  - `fastener_missing`
  - `rail_surface_defect`
  - `sleeper_or_slab_damage`
  - `fence_intrusion_damage`
  - `catenary_or_pole_abnormal`

合成相机路径也支持 `fastener_broken`；真实训练的 YOLO 模型应覆盖用户要求的全部十类故障。

## YOLO 模型

检测模型优先级：

1. `data/models/rail_defects.pt`
2. `data/models/yolov8n.pt`
3. 确定性合成兜底检测器

下载通用 YOLO 权重：

```powershell
.\scripts\download_yolo_weights.ps1
```

检查当前模型资产和实际推理模式：

```powershell
python .\scripts\model_check.py
```

如果要在验收时强制要求真实铁路模型：

```powershell
python .\scripts\model_check.py --require-rail-model
```

如果要接近真实生产效果，应使用铁路巡检数据训练或微调 `rail_defects.pt`。类别名应保持为：

```text
person_on_track
foreign_object
rock_or_debris
fallen_branch
fastener_missing
fastener_broken
rail_surface_defect
sleeper_or_slab_damage
fence_intrusion_damage
catenary_or_pole_abnormal
```

仓库预留了标准 YOLO 数据集结构：

```text
data/datasets/rail_defects_yolo/data.yaml
data/datasets/rail_defects_yolo/images/{train,val,test}
data/datasets/rail_defects_yolo/labels/{train,val,test}
```

校验类别顺序、目录结构和 YOLO 标签格式：

```powershell
python .\scripts\dataset_check.py
```

如果要求真实训练数据必须已经放好：

```powershell
python .\scripts\dataset_check.py -RequireData
```

训练数据不提交到 Git，`data.yaml` 的类别顺序必须和 `fault_catalog.py` 保持一致。

## Web Dashboard

默认地址：

```text
http://localhost:8080
```

Dashboard 展示：

- 无人机状态和电量。
- 当前巡检任务阶段。
- 最新检测结果。
- 告警列表。
- debug image。
- 巡检报告入口。

状态 API：

```text
http://localhost:8080/api/status
```

如果端口冲突，可以在启动脚本中指定其他端口，例如：

```powershell
.\scripts\start_offline_demo.ps1 -DashboardPort 8090
```

## RViz2 可视化

完整仿真默认可启动 RViz2；如果当前 WSL2/WSLg 图形环境不稳定，建议先使用：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz
```

RViz2 配置用于查看：

- 无人机轨迹。
- 巡检目标点。
- 任务 marker。
- 检测和告警位置。
- 关键 ROS topic。
- 感知 debug image。

## 强化学习扩展预留

`rail_inspection_rl` 包预留 Gymnasium 环境封装和策略接口，后续可扩展：

- 用 RL policy 替换规则巡检控制。
- 目标靠近和复查策略。
- 避障和路径规划。
- 巡检效率优化。
- 训练/评估接口。

第一阶段不要求高质量 RL 训练结果，但目录和接口已经按后续研究训练框架预留。

当前可运行的基线评估 smoke：

```powershell
python .\scripts\rl_smoke.py
```

如果在 Docker/ROS 环境内：

```bash
ros2 run rail_inspection_rl rl_policy_eval --episodes 3 --max-steps 360
```

该评估会运行 `RulePolicyAdapter`，输出成功率、平均奖励、最终巡检进度和每回合结果。它只验证第二阶段接口可执行，不代表正式强化学习训练效果。

## 后续发展方向

项目后续建议按“先工程可用，再算法增强，再真实迁移”的顺序推进。

### 阶段 2：真实 YOLO 检测能力

目标是把当前可验收的检测链路替换为真实铁路巡检模型：

- 收集或整理铁路巡检公开数据集和自建合成数据。
- 统一十类缺陷标签：
  - `person_on_track`
  - `foreign_object`
  - `rock_or_debris`
  - `fallen_branch`
  - `fastener_missing`
  - `fastener_broken`
  - `rail_surface_defect`
  - `sleeper_or_slab_damage`
  - `fence_intrusion_damage`
  - `catenary_or_pole_abnormal`
- 训练或微调 `rail_defects.pt`。
- 构建 YOLO 评估脚本，输出 mAP、混淆矩阵、不同光照/距离/角度下的召回率。
- 将 Dashboard 的类别统计和报告字段扩展为多类别巡检结果。

### 阶段 3：场景和传感器增强

目标是让仿真更接近真实高铁巡检任务：

- 扩展线路长度、弯道、坡度、桥隧过渡、站场边界和复杂背景。
- 增加天气、光照、阴影、雾、雨、夜间等扰动。
- 为前视、下视、云台相机分别配置不同内参、视场角和安装姿态。
- 增加深度相机或 LiDAR，用于避障和近距离复查。
- 增加 GPS/RTK 误差、风扰动和定位漂移模型。
- 建立可批量生成缺陷位置和类别的场景参数化脚本。

### 阶段 4：巡检策略和路径规划

目标是从固定规则状态机升级为可比较、可评估的巡检策略：

- 将当前规则巡检策略抽象成 policy interface。
- 增加故障靠近复查、目标重定位、距离保持和绕障逻辑。
- 加入巡检效率指标：覆盖率、误检复查耗时、单位里程耗电、告警定位误差。
- 实现多策略对比：规则策略、启发式策略、RL policy。
- 输出可复现实验报告，比较不同策略在同一线路场景下的表现。

### 阶段 5：Gymnasium + 强化学习训练

目标是在 `rail_inspection_rl` 基础上形成训练框架：

- 封装观测空间：无人机位姿、速度、目标相对位置、图像检测结果、障碍物距离。
- 封装动作空间：速度指令、航点指令、云台角度或复查动作。
- 设计奖励函数：覆盖率、告警发现、复查质量、碰撞惩罚、越界惩罚、能耗惩罚。
- 支持 headless 批量仿真和训练日志记录。
- 预留 Stable-Baselines3、RLlib 或自定义 PyTorch policy 接口。

### 阶段 6：真实无人机迁移

目标是把仿真链路迁移到真实 PX4 飞控 + companion computer：

- 使用 Jetson Orin/Xavier 或等价 companion computer 运行 ROS 2、YOLO 和任务节点。
- 将 Gazebo 相机 topic 替换为真实相机 driver。
- 将仿真状态替换为 PX4 `/fmu/out/*`、GPS/RTK、EKF 和 MAVLink 状态。
- 增加地理围栏、禁飞区、失联返航、低电量返航和人工接管机制。
- 对报告系统接入真实时间、真实经纬度、高铁里程标或线路资产编号。
- 在真实飞行前先进行 HITL/SITL 回归测试和安全评审。

## 真实无人机迁移方向

核心节点避免强绑定 Gazebo：

- 任务/控制节点发布 `/dri/offboard/setpoint`，并可选发布 PX4 `/fmu/in/*` 消息。
- 感知节点订阅标准 ROS 2 `sensor_msgs/Image`，真实相机 driver 可以替换 Gazebo 或合成 publisher。
- 报告和 Dashboard 只消费 `/dri/*` 消息。
- PX4 bridge 使用 uXRCE-DDS，匹配 Jetson Orin/Xavier + PX4 飞控的 companion-computer 部署方式。

真实硬件部署时替换：

- Gazebo 图像 topic 为真实相机 driver topic。
- 仿真 telemetry 为 PX4 `/fmu/out/*` 状态适配器。
- 合成 GPS 为真实 GPS/RTK 或 EKF 输出。
- 规则策略为更严格的地理围栏逻辑或后续 RL policy adapter。

## 故障排查

Docker daemon 不可用：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

处理：

```powershell
.\scripts\start_docker_desktop.ps1
docker info
```

没有 WSL Ubuntu：

```powershell
wsl -l -v
wsl --install -d Ubuntu-22.04
```

容器内看不到 GPU：

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

如果失败，检查 Docker Desktop WSL2 backend 和 NVIDIA container toolkit / GPU integration。

PX4 client 未连接：

- 确认 `MicroXRCEAgent udp4 -p 8888` 正在运行。
- 确认 PX4 SITL 日志中出现 XRCE-DDS client 相关信息。
- 保持 `ROS_DOMAIN_ID` 一致。

Gazebo 在 WSLg 下黑屏或崩溃：

- 先使用 `.\scripts\start_full_sim.ps1 -NoRviz`。
- 默认完整仿真使用 `gz sim -s` server-only 模式，适合 headless 验收。确认 WSLg/X11 渲染可用后再启动 RViz。
- 使用离线 demo 验证 ROS 业务链路。
- 可在容器内用 `glxinfo -B` 检查 GPU/WSLg/OpenGL。

ROS Python 构建找不到 NumPy header，或 `cv_bridge` 报 NumPy ABI 错误：

- Dockerfile 改动后重新构建镜像：`.\scripts\build.ps1`。
- 保持 NumPy 在 ROS Humble 兼容的 1.x ABI。当前 Dockerfile 安装 `python3-numpy`、`numpy<2` 和 `opencv-python-headless<4.12`。
- 用 `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild` 清理旧 workspace 构建产物，或重新运行 `.\scripts\acceptance_offline.ps1`。

Dashboard 不刷新：

- 确认 `/dri/mission/state`、`/dri/drone/telemetry`、`/dri/perception/debug_image` 存在。
- 检查 `http://localhost:8080/api/status`。
- 端口冲突时使用 `.\scripts\start_offline_demo.ps1 -DashboardPort 8090`。

Dashboard 在容器日志中显示启动，但 Windows 访问不了 `localhost:8080`：

- 先检查端口是否映射到宿主机：

```powershell
docker ps --filter name=drone-rail-inspection
```

- 正常应看到：

```text
0.0.0.0:8080->8080/tcp
```

- 如果 `PORTS` 为空，说明容器没有发布 Dashboard 端口。请确认 `compose.yaml` 中存在：

```yaml
ports:
  - "${DRI_DASHBOARD_PORT:-8080}:${DRI_DASHBOARD_PORT:-8080}"
```

- 然后重启 demo：

```powershell
docker rm -f drone-rail-inspection
.\scripts\start_offline_demo.ps1 -DashboardPort 8080
```

- 如果刚启动后浏览器仍暂时打不开，等待 ROS workspace 编译和 launch 完成。日志出现以下内容后再访问：

```text
Uvicorn running on http://0.0.0.0:8080
```

PX4 相机 topic 和默认 bridge 不一致：

```bash
gz topic -l | grep -i camera
```

如果 `gz_x500_depth` 相机 topic 不是 `/world/high_speed_rail_corridor/model/x500_depth_0/link/camera_link/sensor/IMX214/image`，请更新 `ros2_ws/src/rail_inspection_bringup/launch/full_sim.launch.py` 中的 `ros_gz_bridge` 映射。ROS 侧目标 topic 应保持为 `/dri/camera/front/image_raw`。

## 当前已知限制

- 第一阶段高铁世界使用 SDF 工程几何，适合工程验证，不是照片级数字孪生。
- 内置兜底检测器用于确定性合成验收。真实检测精度依赖 `data/models/rail_defects.pt` 中的铁路缺陷训练模型。
- PX4/Gazebo 完整验证依赖主机上的 WSL2 Ubuntu、Docker Desktop daemon 和 NVIDIA/GPU 配置。
- 默认完整验收启用 synthetic camera，保证可重复；真实相机载荷和真实 YOLO 权重属于后续增强。

## 当前下一步建议

如果目标是演示给别人看：

1. 先运行 `.\scripts\start_offline_demo.ps1`，打开 `http://localhost:8080`，展示任务、检测、告警和报告。
2. 再运行 `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild`，用 `.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1` 展示 PX4/Gazebo/ROS2 集成验收。
3. 展示 `data/reports/inspection_report.html` 和 `data/evidence/` 中的证据图片。

如果目标是继续研发：

1. 优先补真实 `rail_defects.pt` 和铁路缺陷数据集。
2. 扩展 Gazebo 场景和相机模型，让检测图像更接近真实巡检。
3. 将任务状态机抽象成可替换 policy，接入 `rail_inspection_rl`。
4. 建立回归验收：每次改动后至少运行 offline acceptance；涉及 PX4/Gazebo 时运行 full acceptance。
