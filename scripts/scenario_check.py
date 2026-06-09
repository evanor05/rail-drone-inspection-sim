#!/usr/bin/env python3
import argparse
import ast
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "data" / "scenarios" / "default_synthetic_faults.json"
FAULT_CATALOG = ROOT / "ros2_ws" / "src" / "rail_inspection_perception" / "rail_inspection_perception" / "fault_catalog.py"


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 1


def load_fault_classes() -> list[str]:
    tree = ast.parse(FAULT_CATALOG.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FAULT_CLASSES":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        return value
    raise ValueError(f"Unable to read FAULT_CLASSES from {FAULT_CATALOG}")


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number, got bool")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _validate_bbox(value: Any, label: str, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label} must be [xmin, ymin, xmax, ymax]")
    bbox = tuple(int(_finite_number(item, f"{label}[{index}]")) for index, item in enumerate(value))
    x1, y1, x2, y2 = bbox
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError(f"{label} out of bounds for {width}x{height}: {bbox}")
    return bbox


def validate_scenario(scenario: dict[str, Any], width: int = 640, height: int = 480) -> list[str]:
    if int(scenario.get("schema_version", 0)) != 1:
        raise ValueError("schema_version must be 1")
    if not str(scenario.get("name", "")).strip():
        raise ValueError("name is required")
    faults = scenario.get("faults")
    if not isinstance(faults, list) or not faults:
        raise ValueError("faults must be a non-empty list")

    fault_classes = load_fault_classes()
    allowed = set(fault_classes)
    seen_classes: set[str] = set()
    previous_kp = -math.inf
    warnings: list[str] = []

    for index, item in enumerate(faults):
        fault = _require_object(item, f"faults[{index}]")
        defect_class = str(fault.get("defect_class", "")).strip()
        if defect_class not in allowed:
            raise ValueError(f"faults[{index}].defect_class {defect_class!r} is not in fault_catalog.py")
        seen_classes.add(defect_class)

        kp_m = _finite_number(fault.get("kp_m"), f"faults[{index}].kp_m")
        if kp_m < 0.0:
            raise ValueError(f"faults[{index}].kp_m must be non-negative")
        if kp_m < previous_kp:
            warnings.append(f"fault {defect_class} at kp_m={kp_m} is not sorted by route progress")
        previous_kp = kp_m

        _finite_number(fault.get("lateral_m"), f"faults[{index}].lateral_m")
        confidence = _finite_number(fault.get("confidence"), f"faults[{index}].confidence")
        if confidence < 0.1 or confidence > 1.0:
            raise ValueError(f"faults[{index}].confidence must be in [0.1, 1.0]")
        _validate_bbox(fault.get("bbox"), f"faults[{index}].bbox", width, height)

    missing_classes = [item for item in fault_classes if item not in seen_classes]
    if missing_classes:
        raise ValueError(f"scenario does not cover fault classes: {missing_classes}")
    return warnings


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("scenario root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DroneRailInspection synthetic fault scenario JSON files.")
    parser.add_argument("scenario", nargs="?", default=str(DEFAULT_SCENARIO), help="Scenario JSON path")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()

    path = Path(args.scenario)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return fail(f"Scenario does not exist: {path}")

    try:
        scenario = load_scenario(path)
        warnings = validate_scenario(scenario, width=args.width, height=args.height)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return fail(f"Scenario validation failed: {exc}")

    print(f"[PASS] Scenario valid: {path}")
    print(f"name={scenario['name']} faults={len(scenario['faults'])}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
