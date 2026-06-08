# 贡献与开发说明

本项目优先保证工程演示链路可运行，再逐步增强研究训练能力。提交代码前请尽量保证静态检查通过，涉及运行链路时补充离线或完整仿真验收结果。

## 分支建议

- `main`：保持可构建、可验收。
- 功能分支：建议使用 `feature/<topic>` 或 `fix/<topic>`。
- 大型改动拆分提交，避免同时改 Docker、PX4、Dashboard 和训练代码。

## 提交前检查

不依赖 Docker 的基础检查：

```powershell
cd E:\DroneRailInspection
python .\scripts\static_check.py
docker compose config --quiet
```

如果只改 README、docs 或 Dashboard 静态文件，至少运行上面的检查。

## 离线链路验证

涉及 Dashboard、报告、检测节点、消息字段或任务状态机时，运行：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\acceptance_offline.ps1 -Seconds 35
```

验收重点：

- `/dri/mission/state`
- `/dri/drone/telemetry`
- `/dri/detections`
- `/dri/alerts`
- `data/reports/inspection_report.*`
- `data/evidence/*`

## 完整仿真验证

涉及 PX4、Gazebo、launch、ROS-Gazebo bridge、uXRCE-DDS 或 offboard 控制时，运行：

```powershell
cd E:\DroneRailInspection
docker rm -f drone-rail-inspection
.\scripts\start_full_sim.ps1 -NoRviz -CleanBuild
```

另开 PowerShell：

```powershell
cd E:\DroneRailInspection
.\scripts\acceptance_full_sim.ps1 -DashboardPort 8080 -MinAlerts 1
```

## 文件管理规则

不要提交：

- Docker build 日志。
- ROS `build/`、`install/`、`log/`。
- `data/evidence/` 运行证据图。
- `data/reports/` 运行报告。
- `.pt`、`.onnx`、`.engine` 模型权重。
- rosbag、MCAP 或 SQLite 录包文件。

保留：

- `data/evidence/.gitkeep`
- `data/reports/.gitkeep`
- 源码、launch、SDF、脚本、文档。

## Dashboard 修改原则

- 页面默认中文，必要时在括号中保留英文 topic/class 名称，便于开发调试。
- 不直接依赖 Gazebo；优先消费 `/dri/*` API 聚合数据。
- 保持移动端和 1280x720 窗口可读。
- 修改后至少运行离线演示或检查静态 HTML/JS。

## YOLO 模型贡献

模型权重不要直接提交 GitHub。建议：

1. 在 issue 或 release 中说明模型来源、类别顺序、训练数据和指标。
2. 权重文件放入 `data/models/rail_defects.pt`。
3. 类别顺序保持 README 中的十类故障名称。
4. 提供评估脚本或 mAP/召回率结果。

## 场景贡献

修改 `high_speed_rail_corridor.sdf` 时注意：

- 保留双线高铁、无砟轨道、接触网、护栏、隧道口、高架/路基等核心元素。
- 新增故障目标时同步更新检测/报告/文档。
- 保持 `scripts/static_check.py` 能检查到关键场景特征。

## PR 描述建议

PR 中建议包含：

- 改动目的。
- 影响模块。
- 已运行的命令和结果。
- 是否影响 Docker 镜像构建。
- 是否影响 PX4/Gazebo 完整仿真。
- 截图或报告样例，如果改动 Dashboard/报告。