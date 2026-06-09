#!/usr/bin/env python3
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "data" / "missions" / "default_corridor_profile.json"
ALLOWED_PHASES = {"TAKEOFF", "ENTER_CORRIDOR", "INSPECT", "REINSPECT", "RETURN", "LAND"}
REQUIRED_WAYPOINT_FIELDS = {"name", "phase", "x", "y", "z", "speed"}


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 1


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


def validate_profile(profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if int(profile.get("schema_version", 0)) != 1:
        raise ValueError("schema_version must be 1")
    if not str(profile.get("name", "")).strip():
        raise ValueError("name is required")
    if profile.get("coordinate_frame") != "map":
        raise ValueError("coordinate_frame must be 'map'")

    route = _require_object(profile.get("route"), "route")
    home = _require_object(route.get("home"), "route.home")
    for key in ("x", "y", "z"):
        _finite_number(home.get(key), f"route.home.{key}")
    start_kp = _finite_number(route.get("start_kp_m"), "route.start_kp_m")
    end_kp = _finite_number(route.get("end_kp_m"), "route.end_kp_m")
    if end_kp <= start_kp:
        raise ValueError("route.end_kp_m must be greater than route.start_kp_m")
    _finite_number(route.get("corridor_y_m"), "route.corridor_y_m")

    reinspection = _require_object(profile.get("reinspection"), "reinspection")
    offset = _require_object(reinspection.get("approach_offset_m"), "reinspection.approach_offset_m")
    for key in ("x", "y", "z"):
        _finite_number(offset.get(key), f"reinspection.approach_offset_m.{key}")
    min_alt = _finite_number(reinspection.get("min_altitude_m"), "reinspection.min_altitude_m")
    max_alt = _finite_number(reinspection.get("max_altitude_m"), "reinspection.max_altitude_m")
    if min_alt < 0.5 or max_alt <= min_alt:
        raise ValueError("reinspection altitude bounds are invalid")
    pause_seconds = _finite_number(reinspection.get("pause_seconds"), "reinspection.pause_seconds")
    if pause_seconds <= 0:
        raise ValueError("reinspection.pause_seconds must be positive")

    waypoints = profile.get("waypoints")
    if not isinstance(waypoints, list) or len(waypoints) < 3:
        raise ValueError("waypoints must contain at least takeoff, inspection and landing points")

    names: set[str] = set()
    phases: list[str] = []
    inspect_count = 0
    previous_x: float | None = None
    for index, item in enumerate(waypoints):
        wp = _require_object(item, f"waypoints[{index}]")
        missing = sorted(REQUIRED_WAYPOINT_FIELDS - set(wp))
        if missing:
            raise ValueError(f"waypoints[{index}] missing fields: {missing}")
        name = str(wp["name"]).strip()
        if not name:
            raise ValueError(f"waypoints[{index}].name is empty")
        if name in names:
            raise ValueError(f"duplicate waypoint name: {name}")
        names.add(name)

        phase = str(wp["phase"]).strip().upper()
        if phase not in ALLOWED_PHASES:
            raise ValueError(f"waypoints[{index}].phase {phase!r} is not allowed")
        phases.append(phase)
        if phase == "INSPECT":
            inspect_count += 1

        x = _finite_number(wp["x"], f"waypoints[{index}].x")
        _finite_number(wp["y"], f"waypoints[{index}].y")
        z = _finite_number(wp["z"], f"waypoints[{index}].z")
        speed = _finite_number(wp["speed"], f"waypoints[{index}].speed")
        if z < 0.0:
            raise ValueError(f"waypoints[{index}].z must be non-negative")
        if speed <= 0.0 or speed > 15.0:
            raise ValueError(f"waypoints[{index}].speed must be in (0, 15] m/s")
        if phase == "INSPECT" and previous_x is not None and x < previous_x:
            warnings.append(f"inspection waypoint {name} moves backward along x")
        if phase == "INSPECT":
            previous_x = x

    if phases[0] != "TAKEOFF":
        raise ValueError("first waypoint phase must be TAKEOFF")
    if phases[-1] != "LAND":
        raise ValueError("last waypoint phase must be LAND")
    if "ENTER_CORRIDOR" not in phases:
        raise ValueError("mission must include ENTER_CORRIDOR")
    if inspect_count < 2:
        raise ValueError("mission must include at least two INSPECT waypoints")
    if "RETURN" not in phases:
        raise ValueError("mission must include RETURN")
    return warnings


def load_profile(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("profile root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DroneRailInspection mission profile JSON files.")
    parser.add_argument("profile", nargs="?", default=str(DEFAULT_PROFILE), help="Mission profile JSON path")
    args = parser.parse_args()

    path = Path(args.profile)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return fail(f"Mission profile does not exist: {path}")

    try:
        profile = load_profile(path)
        warnings = validate_profile(profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return fail(f"Mission profile validation failed: {exc}")

    print(f"[PASS] Mission profile valid: {path}")
    print(f"name={profile['name']} waypoints={len(profile['waypoints'])}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
