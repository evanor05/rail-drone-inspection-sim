# 使用手册：高铁无人机巡检仿真系统

本文说明当前工程如何运行、如何查看 Dashboard、如何执行离线演示、完整 PX4/Gazebo 仿真、RViz2 可视化、报告生成和验收。

## 0. 当前状态

当前项目已经完成第一阶段工程演示闭环，不是从安装 WSL 开始的空项目。

已具备：

- Docker 镜像构建脚本。
- ROS 2 Humble 工作区。
- PX4 SITL + Gazebo Harmonic 完整仿真启动脚本。
- 离线工程演示启动脚本。
- 中文 Web Dashboard。
- 规则巡检任务状态机。
- 合成巡检相机和 YOLO 兼容检测节点。
- 告警 topic、报告生成和证据图输出。
- RViz2 配置。
- Gymnasium/RL 扩展骨架。

默认演示使用 synthetic camera + fallback detector，保证没有真实 YOLO 权重时也能稳定跑通。

RL 扩展接口可以先用轻量 smoke 验证：

```powershell
cd E:\DroneRailInspection
python .\scripts\rl_smoke.py
```

宿主机没有 Gymnasium/Numpy 时该命令会返回 SKIP；在 Docker/ROS 环境内可以运行真实基线评估：

```bash
ros2 run rail_inspection_rl rl_policy_eval --episodes 3 --max-steps 360
```

## 1. 停止当前运行的系统

如果之前启动过 demo 或 full sim，先停止容器：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
```

如果容器不存在，Docker 会提示找不到容器，可以忽略。

## 2. 环境检查

运行：

```powershell
cd E:\DroneRailInspection
.\scripts\doctor.ps1
```

需要确认：

- Docker Desktop 正在运行。
- Docker 使用 WSL2 backend。
- WSL2 Ubuntu 可用。
- `nvidia-smi` 可识别 NVIDIA GPU。
- Docker 容器支持 GPU passthrough。

如果 Docker Desktop 没启动：

```powershell
.\scripts\start_docker_desktop.ps1
```

## 3. 构建 Docker 镜像

默认构建：

```powershell
cd E:\DroneRailInspection
.\scripts\build.ps1
```

如果网络能稳定访问 PyTorch/Ultralytics，并且要启用真实 YOLO 推理依赖：

```powershell
.\scripts\build.ps1 -Ultralytics
```

如果要尝试 CUDA PyTorch wheel：

```powershell
.\scripts\build.ps1 -CudaTorch
```

如果 GitHub 下载 PX4 或 eProsima 依赖不稳定，可以使用可用的 GitHub 镜像前缀：

```powershell
.\scripts\build.ps1 -GitMirrorPrefix "https://your-github-mirror/"
```

## 4. 离线工程演示

离线演示是最快的展示方式，不等待 PX4/Gazebo。它会启动 ROS 2 任务、合成相机、检测、告警、报告和中文 Dashboard。

启动：

```powershell
cd E:\DroneRailInspection
.\scripts\start_offline_demo.ps1
```

默认巡检任务剖面位于：

```text
data\missions\default_corridor_profile.json
```

它定义了起飞点、进入高铁线路走廊、沿轨巡检航点、返航降落和异常复查参数。需要切换任务时，可以复制这份 JSON 后启动：

```powershell
.\scripts\start_offline_demo.ps1 -MissionProfile data\missions\default_corridor_profile.json
```

完整仿真同样支持：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz -MissionProfile data\missions\default_corridor_profile.json
```

任务配置校验：

```powershell
python .\scripts\mission_profile_check.py
```

浏览器打开：

```text
http://127.0.0.1:8080
```

也可以使用：

```text
http://localhost:8080
```

如果端口被占用：

```powershell
docker rm -f drone-rail-inspection
.\scripts\start_offline_demo.ps1 -DashboardPort 8090
```

然后打开：

```text
http://127.0.0.1:8090
```

### Dashboard 页面怎么看

页面主要区域：

- `前视巡检相机 / 检测叠加画面`：显示合成巡检相机画面和检测框。
- `任务阶段`：当前任务流程，例如起飞、进入线路走廊、沿轨巡检、异常复查、返航、降落。
- `巡检进度`：当前航点进度百分比。
- `飞行高度`：无人机当前高度。
- `电量`：仿真电量。
- `最新检测结果`：检测类别、置信度、轨道位置和估计坐标。
- `告警记录`：高风险检测触发的告警，包含严重级别、任务阶段和位置。
- `巡检报告`：打开 HTML 报告。
- `状态 API`：查看 Dashboard 当前 JSON 数据。

典型演示现象：

- 系统发现 `轨道上人员 (person_on_track)`。
- 任务阶段进入 `异常复查`。
- 告警列表持续出现记录。
- 报告文件自动更新。

### 离线演示验收

另开一个 PowerShell：

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_offline.ps1 -Seconds 35
```

通过后会检查：

- ROS 2 工作区构建。
- `/dri/*` topic。
- 检测和告警。
- 报告 JSON/Markdown/HTML。
- 图像证据文件。

## 5. 完整 PX4 + Gazebo 仿真

完整仿真用于验证 PX4 SITL、Gazebo、uXRCE-DDS、ROS 2 bridge、检测、Dashboard 和报告链路。

建议先停止离线 demo：

```powershell
docker rm -f drone-rail-inspection
```

启动完整仿真，不启动 RViz：

```powershell
cd E:\DroneRailInspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

浏览器打开：

```text
http://127.0.0.1:8080
```

完整仿真会启动：

- Gazebo Harmonic headless world。
- PX4 SITL `gz_x500_depth`。
- Micro XRCE-DDS Agent。
- PX4 `/fmu/in/*` 和 `/fmu/out/*` topic。
- ROS-Gazebo image/IMU bridge。
- 合成巡检相机。
- 任务管理、检测、报告和 Dashboard。

### 完整仿真验收

完整仿真运行后，另开 PowerShell：

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

通过后说明：

- `/dri/mission/state` 存在。
- `/dri/drone/telemetry` 存在。
- `/dri/detections` 存在。
- `/dri/alerts` 存在。
- `/dri/perception/debug_image` 存在。
- `/fmu/in/trajectory_setpoint` 存在。
- `/fmu/in/offboard_control_mode` 存在。
- `/fmu/out/vehicle_local_position` 存在。
- Dashboard API 可访问。
- 报告和证据链路可用。

## 6. 启动 RViz2

如果 WSL2/WSLg 图形环境可用，可以启动带 RViz 的完整仿真：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -CleanBuild
```

如果 RViz 黑屏、卡死或 WSLg 图形不稳定，使用：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz
```

RViz2 主要用于查看：

- 无人机路径。
- 航点 marker。
- 告警位置。
- TF。
- debug image。
- 关键 ROS topic。

## 7. ROS 2 topic 调试

进入容器 shell：

```powershell
cd E:\DroneRailInspection
.\scripts\shell.ps1
```

容器内执行：

```bash
source /opt/px4_ros2_ws/install/setup.bash
source /workspace/ros2_ws/install/setup.bash
ros2 topic list
```

常用检查：

```bash
ros2 topic echo --once /dri/mission/state
ros2 topic echo --once /dri/drone/telemetry
ros2 topic echo --once /dri/detections
ros2 topic echo --once /dri/alerts
ros2 topic info /dri/camera/front/image_raw
ros2 topic info /dri/perception/debug_image
```

完整仿真中还可以看：

```bash
ros2 topic info /fmu/in/trajectory_setpoint
ros2 topic info /fmu/in/offboard_control_mode
ros2 topic info /fmu/out/vehicle_local_position
```

## 8. YOLO 模型操作

默认检测优先级：

1. `data/models/rail_defects.pt`
2. `data/models/yolov8n.pt`
3. synthetic fallback detector

下载通用 YOLO 权重：

```powershell
cd E:\DroneRailInspection
.\scripts\download_yolo_weights.ps1
```

检查当前模型资产和实际推理模式：

```powershell
python .\scripts\model_check.py
```

如果验收时必须使用真实铁路缺陷模型：

```powershell
python .\scripts\model_check.py --require-rail-model
```

如果要启用真实 YOLO 推理：

```powershell
.\scripts\build.ps1 -Ultralytics
```

然后把训练好的模型放到：

```text
E:\DroneRailInspection\data\models\rail_defects.pt
```

注意：Git 仓库默认不会上传 `.pt`、`.onnx`、`.engine` 模型文件。

### YOLO 数据集结构

仓库预留了真实铁路缺陷 YOLO 数据集目录：

```text
E:\DroneRailInspection\data\datasets\rail_defects_yolo
  data.yaml
  images\train
  images\val
  images\test
  labels\train
  labels\val
  labels\test
```

校验类别顺序、目录结构和 YOLO 标签格式：

```powershell
cd E:\DroneRailInspection
python .\scripts\dataset_check.py
```

如果要求真实训练数据必须已经放好：

```powershell
python .\scripts\dataset_check.py --require-data
```

`data.yaml` 的十类顺序必须和 `rail_inspection_perception/fault_catalog.py` 保持一致。图片和标签文件属于训练数据，默认不会提交到 Git。

## 9. 报告和证据

报告目录：

```text
E:\DroneRailInspection\data\reports
```

主要文件：

```text
inspection_report.json
inspection_report.md
inspection_report.html
```

证据目录：

```text
E:\DroneRailInspection\data\evidence
```

报告中包含：

- 时间。
- 故障类别。
- 置信度。
- 严重级别。
- 位置。
- 任务阶段。
- 截图或图像证据路径。

报告和证据属于运行产物，默认不提交到 Git。

### 导出演示/验收证据包

演示或验收结束后，可以生成一份独立证据包，方便发给评审、老师、同事或放到 release 附件中：

```powershell
cd E:\DroneRailInspection
.\scripts\export_evidence.ps1 -DashboardPort 8080
```

默认输出目录：

```text
E:\DroneRailInspection\data\exports\inspection-evidence-<timestamp>
```

证据包包含：

- `reports/`：当前 `data/reports` 下的 JSON / Markdown / HTML 报告副本。
- `evidence/`：最近的证据图片或文本证据，默认最多复制 50 个。
- `evidence_manifest.csv`：完整证据文件索引，包含文件名、大小、时间和原始路径。
- `status/dashboard_status.json`：导出时 Dashboard API 快照；如果 Dashboard 未运行，会生成错误说明。
- `status/git_status.txt` 和 `status/git_last_commit.txt`：当前 Git 状态和最新提交。
- `status/docker_ps.txt` 和 `status/docker_info.txt`：Docker 容器状态和 Docker 环境摘要。
- `summary.json`：本次导出的机器可读摘要。

如果证据文件很多，但只想导出索引：

```powershell
.\scripts\export_evidence.ps1 -SkipEvidenceFiles
```

`data/exports` 同样属于运行产物，默认不提交到 Git。

### 中文报告字段说明

当前报告生成模块会同时输出机器可读字段和中文展示字段。

JSON 中保留的核心字段：

- `defect_class`：英文类别 ID，方便程序处理。
- `defect_class_label`：中文类别，例如 `轨道上人员`。
- `defect_class_display`：中文 + 英文类别，例如 `轨道上人员 (person_on_track)`。
- `severity`：英文严重级别。
- `severity_label`：中文严重级别。
- `mission_phase`：英文任务阶段。
- `mission_phase_label`：中文任务阶段。
- `evidence_path`：证据文件路径。

Markdown 和 HTML 报告默认使用中文标题、中文字段名和中文类别说明，适合演示和人工查看；JSON 适合后续接入数据库、线路资产系统或二次分析脚本。

本地验证中文报告模板：

```powershell
cd E:\DroneRailInspection
python .\scripts\report_smoke.py
```

## 10. 常见问题

### 浏览器打不开 Dashboard

先看端口映射：

```powershell
docker ps --filter name=drone-rail-inspection
```

正常应看到：

```text
0.0.0.0:8080->8080/tcp
```

再检查 API：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8080/api/status -UseBasicParsing
```

如果 `PORTS` 为空或容器状态异常：

```powershell
docker rm -f drone-rail-inspection
.\scripts\start_offline_demo.ps1
```

### 页面刚打开没有数据

等待 ROS 2 工作区构建和 launch 完成。日志出现以下内容后再访问：

```text
Uvicorn running on http://0.0.0.0:8080
```

### 看到 ultralytics unavailable

这是正常兜底模式：

```text
ultralytics is unavailable; using synthetic fallback detector.
```

表示当前没有安装 Ultralytics/PyTorch，系统会用合成兜底检测器完成演示和验收。

### 看到 person_on_track 告警

这是业务告警，不是程序错误。含义是系统检测到轨道上人员，任务管理器进入异常复查。

### Gazebo/RViz 图形问题

优先使用 headless：

```powershell
.\scripts\start_full_sim.ps1 -NoRviz
```

等 WSLg/X11/OpenGL 确认可用后，再运行带 RViz 的完整仿真。

## 11. 推荐演示流程

给别人演示时建议按这个顺序：

1. 打开 README，说明项目目标和技术栈。
2. 运行 `.\scripts\start_offline_demo.ps1`。
3. 打开 `http://127.0.0.1:8080`，展示中文 Dashboard。
4. 指出任务阶段从巡检进入异常复查。
5. 展示最新检测结果和告警记录。
6. 打开 `巡检报告`。
7. 说明完整 PX4/Gazebo 验收命令。
8. 如果时间和机器状态允许，再运行 `.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild` 和 full acceptance。

## 12. 推荐研发流程

继续开发时建议：

1. 每次修改前先停止容器。
2. 小改 Dashboard 或报告：运行 offline demo 验证。
3. 改 ROS topic、PX4、Gazebo、launch：运行 full sim 验证。
4. 每次提交前运行：

```powershell
.\scripts\verify_local.ps1
python .\scripts\static_check.py
python .\scripts\mission_profile_check.py
docker compose config --quiet
```

5. 涉及运行链路时补跑：

```powershell
.\scripts\acceptance_offline.ps1 -Seconds 35
```

6. 涉及 PX4/Gazebo 时补跑：

```powershell
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

## 13. 常用辅助脚本

为了降低操作门槛，项目提供了几个常用 PowerShell 脚本。

提交前或演示前预检：

```powershell
cd E:\DroneRailInspection
.\scripts\preflight.ps1
```

如果 Docker Desktop 没启动，但仍想检查除 Compose 外的内容：

```powershell
.\scripts\preflight.ps1 -SkipDockerCompose
```

生成本地综合验证日志：

```powershell
.\scripts\verify_local.ps1
```

它会运行静态检查、中文报告 smoke、PowerShell 脚本解析和证据导出 smoke，并把日志写到：
当前版本还会检查任务剖面、YOLO 数据集结构、YOLO 模型资产和 RL policy smoke；因此它适合在上传 GitHub 或演示前做一次完整本地回归。

```text
E:\DroneRailInspection\data\exports\local-verify-<timestamp>
```

如果还要检查 `docker compose config --quiet`：

```powershell
.\scripts\verify_local.ps1 -WithDockerCompose
```

查看当前状态：

```powershell
cd E:\DroneRailInspection
.\scripts\status.ps1
```

它会显示：

- 当前容器状态。
- Dashboard API 是否可访问。
- 当前任务阶段、目标、告警数量、检测数量。
- 报告文件列表。
- 证据文件数量。

打开 Dashboard：

```powershell
.\scripts\open_dashboard.ps1
```

如果 Dashboard 使用其他端口：

```powershell
.\scripts\open_dashboard.ps1 -DashboardPort 8090
```

停止仿真：

```powershell
.\scripts\stop_sim.ps1
```

交互式演示菜单：

```powershell
.\scripts\demo_menu.ps1
```

菜单包含：

- 查看状态。
- 启动离线工程演示。
- 启动完整 PX4/Gazebo 仿真。
- 打开 Dashboard。
- 运行离线验收。
- 运行完整仿真验收。
- 运行本地综合验证。
- 导出演示/验收证据包。
- 停止仿真容器。
- 打开容器 shell。
