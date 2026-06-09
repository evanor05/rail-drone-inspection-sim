import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


MODEL_PRIORITY = [
    ("rail_defects.pt", "rail_specific_yolo", "rail-specific PyTorch YOLO model"),
    ("rail_defects.onnx", "rail_specific_onnx", "rail-specific ONNX export"),
    ("rail_defects.engine", "rail_specific_tensorrt", "rail-specific TensorRT export"),
    ("yolov8n.pt", "generic_yolo", "generic Ultralytics YOLO model"),
]


def _path_summary(path_value: str) -> Dict[str, Any]:
    path = Path(path_value) if path_value else Path()
    exists = path.exists() if path_value else False
    summary: Dict[str, Any] = {
        "path": path_value,
        "name": path.name if path_value else "",
        "exists": exists,
    }
    if exists and path.is_file():
        summary["size_bytes"] = path.stat().st_size
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
            summary["config_name"] = payload.get("name", "")
            if isinstance(payload.get("waypoints"), list):
                summary["waypoints"] = len(payload["waypoints"])
            if isinstance(payload.get("faults"), list):
                summary["faults"] = len(payload["faults"])
        except Exception as exc:
            summary["read_error"] = str(exc)
    return summary


def _inspect_model_dir(model_dir_value: str) -> Dict[str, Any]:
    model_dir = Path(model_dir_value)
    models = []
    selected = None
    for filename, mode, role in MODEL_PRIORITY:
        path = model_dir / filename
        exists = path.exists()
        entry = {
            "name": path.stem,
            "path": str(path),
            "exists": exists,
            "role": role,
            "size_bytes": path.stat().st_size if exists else 0,
        }
        models.append(entry)
        if selected is None and exists:
            selected = {
                "name": path.stem,
                "path": str(path),
                "mode": mode,
                "role": role,
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
        "models": models,
        "expected_runtime_priority": [item[0] for item in MODEL_PRIORITY],
    }


class RuntimeInfoPublisher(Node):
    """Publishes reproducibility metadata for dashboard, reports, and evidence export."""

    def __init__(self) -> None:
        super().__init__("runtime_info_publisher")
        self.declare_parameter("mission_profile_path", "/workspace/data/missions/default_corridor_profile.json")
        self.declare_parameter("scenario_path", "/workspace/data/scenarios/default_synthetic_faults.json")
        self.declare_parameter("model_dir", "/workspace/data/models")
        self.declare_parameter("mode", "offline_or_sitl")
        self.publisher = self.create_publisher(String, "/dri/runtime/info", 10)
        self.payload = self._build_payload()
        self.timer = self.create_timer(2.0, self._publish)
        self._publish()

    def _build_payload(self) -> Dict[str, Any]:
        mission_profile = str(self.get_parameter("mission_profile_path").value or "")
        scenario = str(self.get_parameter("scenario_path").value or "")
        model_dir = str(self.get_parameter("model_dir").value or "/workspace/data/models")
        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": str(self.get_parameter("mode").value or "offline_or_sitl"),
            "ros_domain_id": os.environ.get("ROS_DOMAIN_ID", ""),
            "rmw_implementation": os.environ.get("RMW_IMPLEMENTATION", ""),
            "dashboard_port": os.environ.get("DRI_DASHBOARD_PORT", ""),
            "mission_profile": _path_summary(mission_profile),
            "synthetic_scenario": _path_summary(scenario),
            "model_assets": _inspect_model_dir(model_dir),
            "workspace": os.environ.get("DRI_WORKSPACE", "/workspace"),
        }

    def _publish(self) -> None:
        msg = String()
        msg.data = json.dumps(self.payload, ensure_ascii=False, sort_keys=True)
        self.publisher.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RuntimeInfoPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
