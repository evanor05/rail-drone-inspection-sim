#!/usr/bin/env python3
import argparse
import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "datasets" / "rail_defects_yolo"
FAULT_CATALOG = ROOT / "ros2_ws" / "src" / "rail_inspection_perception" / "rail_inspection_perception" / "fault_catalog.py"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 1


def load_fault_classes() -> List[str]:
    spec = importlib.util.spec_from_file_location("fault_catalog", FAULT_CATALOG)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return list(module.FAULT_CLASSES)


def parse_names(data_yaml: Path) -> List[str]:
    names: Dict[int, str] = {}
    in_names = False
    for raw_line in data_yaml.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if re.match(r"^names\s*:", line):
            in_names = True
            continue
        if in_names:
            if not raw_line.startswith((" ", "\t")):
                break
            match = re.match(r"\s*(\d+)\s*:\s*([A-Za-z0-9_]+)\s*$", raw_line)
            if match:
                names[int(match.group(1))] = match.group(2)
    if not names:
        raise ValueError(f"No names mapping found in {data_yaml}")
    return [names[index] for index in sorted(names)]


def check_required_dirs(dataset: Path) -> List[str]:
    required = [
        "images/train",
        "images/val",
        "images/test",
        "labels/train",
        "labels/val",
        "labels/test",
    ]
    missing = [rel for rel in required if not (dataset / rel).is_dir()]
    return missing


def iter_label_files(dataset: Path) -> List[Path]:
    return sorted(path for path in (dataset / "labels").rglob("*.txt") if path.is_file())


def validate_label_file(path: Path, class_count: int) -> List[str]:
    errors: List[str] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            errors.append(f"{path}:{line_no}: expected 5 fields, got {len(parts)}")
            continue
        try:
            class_id = int(parts[0])
            values = [float(item) for item in parts[1:]]
        except ValueError:
            errors.append(f"{path}:{line_no}: non-numeric YOLO label")
            continue
        if not 0 <= class_id < class_count:
            errors.append(f"{path}:{line_no}: class_id {class_id} out of range 0..{class_count - 1}")
        for value in values:
            if not 0.0 <= value <= 1.0:
                errors.append(f"{path}:{line_no}: normalized coordinate {value} outside [0, 1]")
    return errors


def count_images(dataset: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for split in ("train", "val", "test"):
        image_dir = dataset / "images" / split
        counts[split] = sum(1 for path in image_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    return counts


def count_labels(dataset: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for split in ("train", "val", "test"):
        label_dir = dataset / "labels" / split
        counts[split] = sum(1 for path in label_dir.rglob("*.txt") if path.is_file())
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the reserved YOLO railway defect dataset structure.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--require-data", action="store_true", help="Fail when train/val images or labels are missing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = args.dataset.resolve()
    data_yaml = dataset / "data.yaml"
    if not data_yaml.exists():
        return fail(f"Missing data.yaml: {data_yaml}")

    missing_dirs = check_required_dirs(dataset)
    if missing_dirs:
        return fail(f"Missing dataset directories: {missing_dirs}")

    expected_classes = load_fault_classes()
    yaml_classes = parse_names(data_yaml)
    if yaml_classes != expected_classes:
        return fail(f"data.yaml class names do not match fault_catalog.py: {yaml_classes} != {expected_classes}")

    label_errors: List[str] = []
    for label_file in iter_label_files(dataset):
        label_errors.extend(validate_label_file(label_file, len(expected_classes)))
    if label_errors:
        for error in label_errors[:20]:
            print(error, file=sys.stderr)
        return fail(f"Invalid YOLO labels: {len(label_errors)} issue(s)")

    image_counts = count_images(dataset)
    label_counts = count_labels(dataset)
    print(f"[PASS] Dataset class mapping: {len(expected_classes)} classes")
    print(f"[INFO] Image counts: {image_counts}")
    print(f"[INFO] Label counts: {label_counts}")

    has_required_data = image_counts["train"] > 0 and image_counts["val"] > 0 and label_counts["train"] > 0 and label_counts["val"] > 0
    if args.require_data and not has_required_data:
        return fail("Dataset is structurally valid but train/val images and labels are missing.")
    if not has_required_data:
        print("[WARN] Dataset structure is ready, but train/val data is not populated yet.")
    print("[PASS] YOLO dataset check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
