#!/usr/bin/env python3
import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {"build", "install", "log"}


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 1


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8-sig")


def parse_python() -> int:
    for path in ROOT.rglob("*.py"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return fail(f"Python syntax error in {path}: {exc}")
    print("[PASS] Python syntax")
    return 0


def parse_xml() -> int:
    for path in list(ROOT.rglob("package.xml")) + list(ROOT.rglob("*.sdf")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            return fail(f"XML/SDF parse error in {path}: {exc}")
    print("[PASS] XML/SDF parse")
    return 0


def required_files() -> int:
    files = [
        "compose.yaml",
        "docker/Dockerfile",
        "docker/entrypoint.sh",
        "README.md",
        "CONTRIBUTING.md",
        ".github/workflows/static-validation.yml",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        "docs/USAGE_CN.md",
        "docs/DEMO_SCRIPT_CN.md",
        "docs/ARCHITECTURE.md",
        "docs/REQUIREMENTS_TRACE.md",
        "data/missions/default_corridor_profile.json",
        "data/scenarios/default_synthetic_faults.json",
        "data/datasets/rail_defects_yolo/data.yaml",
        "data/datasets/rail_defects_yolo/README.md",
        "data/datasets/rail_defects_yolo/images/train/.gitkeep",
        "data/datasets/rail_defects_yolo/images/val/.gitkeep",
        "data/datasets/rail_defects_yolo/images/test/.gitkeep",
        "data/datasets/rail_defects_yolo/labels/train/.gitkeep",
        "data/datasets/rail_defects_yolo/labels/val/.gitkeep",
        "data/datasets/rail_defects_yolo/labels/test/.gitkeep",
        "ros2_ws/src/rail_inspection_rl/rail_inspection_rl/evaluate.py",
        "ros2_ws/src/rail_inspection_control/rail_inspection_control/runtime_info_publisher.py",
        "ros2_ws/src/rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf",
        "ros2_ws/src/rail_inspection_bringup/launch/offline_demo.launch.py",
        "ros2_ws/src/rail_inspection_bringup/launch/full_sim.launch.py",
        "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/index.html",
        "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/app.js",
        "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/styles.css",
        "scripts/acceptance_offline.ps1",
        "scripts/acceptance_full_sim.ps1",
        "scripts/status.ps1",
        "scripts/stop_sim.ps1",
        "scripts/open_dashboard.ps1",
        "scripts/demo_menu.ps1",
        "scripts/preflight.ps1",
        "scripts/export_evidence.ps1",
        "scripts/verify_local.ps1",
        "scripts/rl_smoke.py",
        "scripts/dataset_check.py",
        "scripts/model_check.py",
        "scripts/mission_profile_check.py",
        "scripts/scenario_check.py",
        "data/exports/.gitkeep",
    ]
    missing = [file for file in files if not (ROOT / file).exists()]
    if missing:
        return fail(f"Missing required files: {missing}")
    print("[PASS] Required files")
    return 0


def require_terms(rel_path: str, terms: list[str], label: str) -> int:
    text = read_text(rel_path)
    missing = [term for term in terms if term not in text]
    if missing:
        return fail(f"{label} missing terms in {rel_path}: {missing}")
    return 0


def scan_world_features() -> int:
    terms = [
        "double_track",
        "ballastless",
        "catenary",
        "fence",
        "tunnel",
        "viaduct",
        "person_on_track",
        "fallen_branch",
        "rail_surface_defect",
        "front_rgb_camera",
        "down_rgb_camera",
        "imu",
    ]
    code = require_terms("ros2_ws/src/rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf", terms, "World feature coverage")
    if code:
        return code
    print("[PASS] World feature coverage")
    return 0


def scan_dashboard_localization() -> int:
    checks = [
        (
            "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/index.html",
            ["高铁无人机巡检调度台", "巡检报告", "状态 API", "运行时长", "当前位置", "告警记录"],
        ),
        (
            "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/app.js",
            ["轨道上人员", "异常复查", "证据：", "formatDuration", "实时调试图像", "Dashboard 刷新失败"],
        ),
        (
            "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/styles.css",
            ["status-strip", "camera-caption", "evidence"],
        ),
    ]
    for rel_path, terms in checks:
        code = require_terms(rel_path, terms, "Dashboard localization")
        if code:
            return code
    print("[PASS] Dashboard localization")
    return 0


def scan_docs() -> int:
    checks = [
        ("README.md", ["快速入口", "docs/USAGE_CN.md", "docs/DEMO_SCRIPT_CN.md", "CONTRIBUTING.md", "demo_menu.ps1"]),
        ("docs/USAGE_CN.md", ["离线工程演示", "完整 PX4 + Gazebo 仿真", "常用辅助脚本", "YOLO", "报告和证据", "导出演示/验收证据包", "本地综合验证日志", "rl_smoke.py", "dataset_check.py", "model_check.py"]),
        ("docs/DEMO_SCRIPT_CN.md", ["演示脚本与仿真操作矩阵", "仿真模式矩阵", "交互式菜单演示"]),
        ("docs/ARCHITECTURE.md", ["架构说明", "Topic 合约", "真实无人机迁移边界", "RL 扩展点", "rl_policy_eval"]),
        ("docs/REQUIREMENTS_TRACE.md", ["需求追踪与验收矩阵", "第一阶段工程演示目标", "真实无人机迁移方向", "当前剩余风险", "RL 接口 smoke"]),
        ("CONTRIBUTING.md", ["提交前检查", "离线链路验证", "完整仿真验证", "Dashboard 修改原则"]),
    ]
    for rel_path, terms in checks:
        code = require_terms(rel_path, terms, "Documentation coverage")
        if code:
            return code
    print("[PASS] Documentation coverage")
    return 0


def scan_mission_profile() -> int:
    try:
        import importlib.util

        module_path = ROOT / "scripts" / "mission_profile_check.py"
        spec = importlib.util.spec_from_file_location("mission_profile_check", module_path)
        if spec is None or spec.loader is None:
            return fail("Unable to load mission_profile_check.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        profile = module.load_profile(ROOT / "data" / "missions" / "default_corridor_profile.json")
        module.validate_profile(profile)
    except Exception as exc:
        return fail(f"Mission profile coverage failed: {exc}")
    code = require_terms(
        "data/missions/default_corridor_profile.json",
        ["default_high_speed_rail_corridor", "reinspection", "inspect_kp_000_120", "land_staging_pad"],
        "Mission profile",
    )
    if code:
        return code
    code = require_terms(
        "ros2_ws/src/rail_inspection_control/rail_inspection_control/mission_manager.py",
        ["mission_profile_path", "ReinspectionConfig", "_load_mission_profile"],
        "Mission manager profile support",
    )
    if code:
        return code
    print("[PASS] Mission profile coverage")
    return 0


def scan_synthetic_scenario() -> int:
    try:
        import importlib.util

        module_path = ROOT / "scripts" / "scenario_check.py"
        spec = importlib.util.spec_from_file_location("scenario_check", module_path)
        if spec is None or spec.loader is None:
            return fail("Unable to load scenario_check.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        scenario = module.load_scenario(ROOT / "data" / "scenarios" / "default_synthetic_faults.json")
        module.validate_scenario(scenario)
    except Exception as exc:
        return fail(f"Synthetic scenario coverage failed: {exc}")
    code = require_terms(
        "data/scenarios/default_synthetic_faults.json",
        ["default_synthetic_faults", "person_on_track", "fastener_broken", "sleeper_or_slab_damage"],
        "Synthetic scenario",
    )
    if code:
        return code
    code = require_terms(
        "ros2_ws/src/rail_inspection_perception/rail_inspection_perception/synthetic_scene_publisher.py",
        ["scenario_path", "DRI_SYNTHETIC_SCENARIO_PATH", "_load_synthetic_faults"],
        "Synthetic scene scenario support",
    )
    if code:
        return code
    print("[PASS] Synthetic scenario coverage")
    return 0


def scan_github_metadata() -> int:
    workflow = read_text(".github/workflows/static-validation.yml")
    terms = ["name: Static Validation", "push:", "pull_request:", "ubuntu-22.04", "python scripts/static_check.py"]
    missing = [term for term in terms if term not in workflow]
    if missing:
        return fail(f"GitHub workflow missing terms: {missing}")
    issue_terms = ["Bug report", "运行模式", "复现步骤", "环境"]
    code = require_terms(".github/ISSUE_TEMPLATE/bug_report.md", issue_terms, "GitHub bug template")
    if code:
        return code
    feature_terms = ["Feature request", "目标", "验收方式"]
    code = require_terms(".github/ISSUE_TEMPLATE/feature_request.md", feature_terms, "GitHub feature template")
    if code:
        return code
    print("[PASS] GitHub metadata")
    return 0


def scan_gitignore() -> int:
    terms = [
        "data/models/*.pt",
        "data/models/*.onnx",
        "data/datasets/**/images/*",
        "!data/datasets/**/images/.gitkeep",
        "data/datasets/**/labels/*",
        "!data/datasets/**/labels/.gitkeep",
        "data/reports/*",
        "!data/reports/.gitkeep",
        "data/evidence/*",
        "!data/evidence/.gitkeep",
        "data/exports/*",
        "!data/exports/.gitkeep",
        "*.bag",
        "*.mcap",
        "*.log",
    ]
    code = require_terms(".gitignore", terms, "Git ignore rules")
    if code:
        return code
    print("[PASS] Git ignore rules")
    return 0


def scan_powershell_scripts() -> int:
    scripts = [
        "scripts/status.ps1",
        "scripts/stop_sim.ps1",
        "scripts/open_dashboard.ps1",
        "scripts/demo_menu.ps1",
        "scripts/preflight.ps1",
        "scripts/export_evidence.ps1",
        "scripts/verify_local.ps1",
        "scripts/start_offline_demo.ps1",
        "scripts/start_full_sim.ps1",
    ]
    for rel_path in scripts:
        text = read_text(rel_path)
        if "$Root = Split-Path -Parent $PSScriptRoot" not in text and rel_path != "scripts/open_dashboard.ps1":
            return fail(f"PowerShell script does not anchor to project root: {rel_path}")
    code = require_terms("scripts/demo_menu.ps1", ["启动离线工程演示", "启动完整 PX4/Gazebo 仿真", "运行完整仿真验收", "运行本地综合验证", "导出演示/验收证据包"], "Demo menu")
    if code:
        return code
    code = require_terms("scripts/export_evidence.ps1", ["inspection-evidence", "evidence_manifest.csv", "dashboard_status.json", "git_last_commit.txt"], "Evidence export")
    if code:
        return code
    code = require_terms("scripts/export_evidence.ps1", ["runtime_info.json", "mission_profile", "synthetic_scenario", "model_assets"], "Evidence runtime export")
    if code:
        return code
    code = require_terms("scripts/verify_local.ps1", ["local-verify", "Static project validation", "YOLO dataset structure check", "YOLO model asset check", "RL policy smoke", "Evidence export smoke", "summary.json"], "Local verification")
    if code:
        return code
    code = require_terms("scripts/report_smoke.py", ["--output-root", "output_root", "inspection_report_smoke.html"], "Report smoke")
    if code:
        return code
    code = require_terms("scripts/rl_smoke.py", ["--require-runtime", "rl_policy_eval_smoke.json", "gymnasium"], "RL smoke")
    if code:
        return code
    code = require_terms("scripts/dataset_check.py", ["--require-data", "fault_catalog.py", "YOLO dataset check complete"], "Dataset check")
    if code:
        return code
    code = require_terms("scripts/model_check.py", ["--require-rail-model", "synthetic_fallback", "rail_defects.pt"], "Model check")
    if code:
        return code
    code = require_terms("scripts/mission_profile_check.py", ["default_corridor_profile.json", "TAKEOFF", "ENTER_CORRIDOR", "LAND"], "Mission profile check")
    if code:
        return code
    code = require_terms("scripts/scenario_check.py", ["default_synthetic_faults.json", "FAULT_CLASSES", "bbox"], "Scenario check")
    if code:
        return code
    code = require_terms("scripts/start_offline_demo.ps1", ["MissionProfile", "Scenario", "mission_profile_path", "scenario_path"], "Offline profile/scenario launch")
    if code:
        return code
    code = require_terms("scripts/start_full_sim.ps1", ["MissionProfile", "Scenario", "mission_profile_path", "scenario_path"], "Full profile/scenario launch")
    if code:
        return code
    code = require_terms("scripts/acceptance_offline.ps1", ["MissionProfile", "Scenario", "mission_profile_path", "scenario_path"], "Offline acceptance profile/scenario launch")
    if code:
        return code
    code = require_terms("ros2_ws/src/rail_inspection_rl/rail_inspection_rl/evaluate.py", ["success_rate", "RulePolicyAdapter", "mean_total_reward"], "RL evaluation")
    if code:
        return code
    code = require_terms("ros2_ws/src/rail_inspection_control/rail_inspection_control/runtime_info_publisher.py", ["/dri/runtime/info", "mission_profile", "synthetic_scenario", "model_assets"], "Runtime info publisher")
    if code:
        return code
    code = require_terms("ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/web_dashboard.py", ["/dri/runtime/info", "runtime"], "Dashboard runtime info")
    if code:
        return code
    code = require_terms("ros2_ws/src/rail_inspection_report/rail_inspection_report/report_templates.py", ["运行配置", "任务剖面", "模型模式", "runtime_lines"], "Report runtime section")
    if code:
        return code
    code = require_terms("scripts/report_smoke.py", ["运行配置", "模型模式", "default_synthetic_faults"], "Report smoke runtime section")
    if code:
        return code
    code = require_terms("data/datasets/rail_defects_yolo/data.yaml", ["person_on_track", "fastener_broken", "catenary_or_pole_abnormal"], "YOLO data.yaml")
    if code:
        return code
    print("[PASS] PowerShell helper scripts")
    return 0


def scan_js_syntax_smoke() -> int:
    text = read_text("ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/app.js")
    pairs = [("{", "}"), ("(", ")"), ("[", "]")]
    for left, right in pairs:
        if text.count(left) != text.count(right):
            return fail(f"Dashboard JS has unbalanced {left}{right}")
    if re.search(r"\$\{[^}]*$", text):
        return fail("Dashboard JS appears to contain an unfinished template expression")
    print("[PASS] Dashboard JS smoke")
    return 0


def main() -> int:
    checks = [
        required_files,
        parse_python,
        parse_xml,
        scan_world_features,
        scan_dashboard_localization,
        scan_docs,
        scan_mission_profile,
        scan_synthetic_scenario,
        scan_github_metadata,
        scan_gitignore,
        scan_powershell_scripts,
        scan_js_syntax_smoke,
    ]
    for check in checks:
        code = check()
        if code:
            return code
    print("[PASS] Static project validation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
