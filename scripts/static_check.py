#!/usr/bin/env python3
import ast
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 1


def parse_python() -> int:
    for path in ROOT.rglob("*.py"):
        if any(part in {"build", "install", "log"} for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return fail(f"Python syntax error in {path}: {exc}")
    print("[PASS] Python syntax")
    return 0


def parse_xml() -> int:
    for path in list(ROOT.rglob("package.xml")) + list(ROOT.rglob("*.sdf")):
        if any(part in {"build", "install", "log"} for part in path.parts):
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
        "README.md",
        "ros2_ws/src/rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf",
        "ros2_ws/src/rail_inspection_bringup/launch/offline_demo.launch.py",
        "ros2_ws/src/rail_inspection_bringup/launch/full_sim.launch.py",
        "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static/index.html",
        "scripts/acceptance_offline.ps1",
    ]
    missing = [file for file in files if not (ROOT / file).exists()]
    if missing:
        return fail(f"Missing required files: {missing}")
    print("[PASS] Required files")
    return 0


def scan_world_features() -> int:
    text = (ROOT / "ros2_ws/src/rail_inspection_gazebo/worlds/high_speed_rail_corridor.sdf").read_text(encoding="utf-8")
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
    missing = [term for term in terms if term not in text]
    if missing:
        return fail(f"World missing feature terms: {missing}")
    print("[PASS] World feature coverage")
    return 0


def main() -> int:
    checks = [required_files, parse_python, parse_xml, scan_world_features]
    for check in checks:
        code = check()
        if code:
            return code
    print("[PASS] Static project validation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
