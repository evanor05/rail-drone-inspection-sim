#!/usr/bin/env python3
import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RL_SRC = ROOT / "ros2_ws" / "src" / "rail_inspection_rl"


def dependency_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the RL baseline evaluation smoke test when dependencies are available.")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=360)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "exports" / "rl_policy_eval_smoke.json")
    parser.add_argument("--require-runtime", action="store_true", help="Fail instead of skip when numpy/gymnasium are unavailable.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    missing = [name for name in ("numpy", "gymnasium") if not dependency_available(name)]
    if missing:
        payload = {
            "status": "SKIP",
            "reason": "Missing optional RL runtime dependencies.",
            "missing": missing,
            "hint": "Run inside the Docker/ROS environment, or install numpy and gymnasium locally.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if args.require_runtime else 0

    sys.path.insert(0, str(RL_SRC))
    from rail_inspection_rl.evaluate import main as eval_main

    sys.argv = [
        "rl_smoke",
        "--episodes",
        str(args.episodes),
        "--max-steps",
        str(args.max_steps),
        "--seed",
        str(args.seed),
        "--output",
        str(args.output),
    ]
    return int(eval_main())


if __name__ == "__main__":
    raise SystemExit(main())
