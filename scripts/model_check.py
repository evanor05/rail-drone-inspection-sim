#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "data" / "models"

MODEL_PRIORITY = [
    {
        "name": "rail_defects_pt",
        "path": "rail_defects.pt",
        "role": "rail-specific PyTorch YOLO model",
        "mode": "rail_specific_yolo",
    },
    {
        "name": "rail_defects_onnx",
        "path": "rail_defects.onnx",
        "role": "rail-specific ONNX export",
        "mode": "rail_specific_onnx",
    },
    {
        "name": "rail_defects_engine",
        "path": "rail_defects.engine",
        "role": "rail-specific TensorRT export",
        "mode": "rail_specific_tensorrt",
    },
    {
        "name": "generic_yolov8n",
        "path": "yolov8n.pt",
        "role": "generic Ultralytics YOLO model",
        "mode": "generic_yolo",
    },
]


def inspect_models(model_dir: Path) -> Dict:
    entries: List[Dict] = []
    selected = None
    for item in MODEL_PRIORITY:
        path = model_dir / item["path"]
        exists = path.exists()
        entry = {
            "name": item["name"],
            "path": str(path),
            "exists": exists,
            "role": item["role"],
            "size_bytes": path.stat().st_size if exists else 0,
        }
        entries.append(entry)
        if selected is None and exists:
            selected = {
                "name": item["name"],
                "path": str(path),
                "mode": item["mode"],
                "role": item["role"],
            }
    if selected is None:
        selected = {
            "name": "synthetic_fallback",
            "path": "",
            "mode": "synthetic_fallback",
            "role": "deterministic synthetic detector used for demos and acceptance",
        }
    return {
        "model_dir": str(model_dir),
        "selected": selected,
        "models": entries,
        "expected_runtime_priority": [item["path"] for item in MODEL_PRIORITY],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect YOLO model assets and report the active inference mode.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--require-rail-model", action="store_true", help="Fail unless a rail-specific model artifact exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_dir = args.model_dir.resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    payload = inspect_models(model_dir)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    selected_mode = payload["selected"]["mode"]
    if args.require_rail_model and not selected_mode.startswith("rail_specific"):
        print("[FAIL] rail_defects.pt/.onnx/.engine is required but not present.", file=sys.stderr)
        return 1
    if selected_mode == "synthetic_fallback":
        print("[WARN] No YOLO model asset found; detector will use synthetic fallback.")
    elif selected_mode == "generic_yolo":
        print("[WARN] Generic yolov8n.pt found; rail-specific classes still require rail_defects.pt.")
    else:
        print("[PASS] Rail-specific model asset found.")
    print("[PASS] Model asset check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
